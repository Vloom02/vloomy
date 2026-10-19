package com.vloomy

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.ToneGenerator
import android.os.IBinder
import android.os.PowerManager
import android.speech.tts.TextToSpeech
import android.util.Log
import com.vloomy.wake.Vad
import com.vloomy.wake.WakeWord
import java.util.Locale
import kotlin.concurrent.thread

/**
 * Escucha siempre en primer plano: wake word → bip → graba hasta que te callás → manda a la PC → dice la respuesta.
 * Mismos umbrales que voice/vloomy.py.
 */
class VloomyService : Service() {
    @Volatile private var activo = false
    @Volatile private var forzar = false
    private var hilo: Thread? = null
    private lateinit var tts: TextToSpeech
    private val bip = ToneGenerator(AudioManager.STREAM_MUSIC, 80)
    private var wakeLock: PowerManager.WakeLock? = null
    private var utterance = 0

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CANAL, "Vloomy escuchando", NotificationManager.IMPORTANCE_LOW))
        tts = TextToSpeech(this) { estado ->
            if (estado == TextToSpeech.SUCCESS &&
                tts.setLanguage(Locale("es", "AR")) < TextToSpeech.LANG_AVAILABLE) {
                tts.setLanguage(Locale("es"))
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, notificacion("Decí \"Hey Jarvis\""), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        if (intent?.action == HABLAR) forzar = true
        if (hilo == null) {
            activo = true
            wakeLock = getSystemService(PowerManager::class.java)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "vloomy:escucha").apply { acquire() }
            hilo = thread(name = "vloomy") { bucle() }
        }
        // Android 14+ no deja reabrir el micrófono desde segundo plano: si el sistema lo mata, se reactiva desde la app.
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        activo = false
        hilo?.join(2_000)
        tts.shutdown()
        bip.release()
        wakeLock?.release()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun bucle() {
        val prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE)
        val servidor = Servidor(prefs.getString("url", "")!!, prefs.getString("token", "")!!)
        val minimo = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val grabador = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000, AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT, maxOf(minimo, WakeWord.BLOQUE * 2 * 8))
        val modelos = WakeWord.incluidos()  // "hey jarvis" y, si está entrenado, "hey vloomy"
        val umbrales = modelos.map { it.second }
        try {
            WakeWord(modelos.map { it.first }).use { wake ->
                Vad().use { vad ->
                    grabador.startRecording()
                    val bloque = ShortArray(WakeWord.BLOQUE)
                    while (activo) {
                        leer(grabador, bloque)
                        val puntajes = wake.procesar(bloque)
                        if (forzar || puntajes.indices.any { puntajes[it] >= umbrales[it] }) {
                            forzar = false
                            atender(grabador, vad, servidor)
                            vaciar(grabador)
                            wake.reset()
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "se cortó la escucha", e)
            avisar("Error: ${e.message}")
        } finally {
            grabador.stop()
            grabador.release()
        }
    }

    private fun atender(grabador: AudioRecord, vad: Vad, servidor: Servidor) {
        bip.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
        avisar("Te escucho…")
        val audio = escuchar(grabador, vad) ?: return avisar("Decí \"Hey Jarvis\"")
        avisar("Pensando…")
        try {
            servidor.voz(audio) { evento ->
                when {
                    evento.has("vos") -> avisar("Vos: ${evento.getString("vos")}")
                    evento.has("decir") -> decir(evento.getString("decir"))
                    evento.has("preguntar") -> {
                        decir(evento.getString("preguntar"))
                        esperarVoz()
                        vaciar(grabador)
                        bip.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
                        servidor.responder(evento.getString("id"), escuchar(grabador, vad) ?: ShortArray(1600))
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "falló el pedido", e)
            decir("No me pude conectar con la PC.")
        }
        esperarVoz()
        avisar("Decí \"Hey Jarvis\"")
    }

    /** Graba desde que hablás hasta ~0,8 s de silencio. null si no dijiste nada en ~5 s. */
    private fun escuchar(grabador: AudioRecord, vad: Vad): ShortArray? {
        vad.reset()
        val trozos = mutableListOf<ShortArray>()
        var hablo = false
        var callado = 0
        for (i in 0 until HABLA_MAX) {
            val x = ShortArray(WakeWord.BLOQUE)
            leer(grabador, x)
            trozos += x
            if (vad.probabilidad(x) > VAD_UMBRAL) {
                hablo = true
                callado = 0
            } else if (hablo) {
                if (++callado >= SILENCIO_FIN) break
            } else if (i >= ESPERA_MAX) {
                return null
            }
        }
        if (!hablo) return null
        return ShortArray(trozos.size * WakeWord.BLOQUE).also { todo ->
            trozos.forEachIndexed { i, t -> t.copyInto(todo, i * WakeWord.BLOQUE) }
        }
    }

    private fun leer(grabador: AudioRecord, destino: ShortArray) {
        var leido = 0
        while (leido < destino.size) {
            val n = grabador.read(destino, leido, destino.size - leido)
            if (n < 0) error("el micrófono devolvió $n")
            leido += n
        }
    }

    /** Descarta lo que grabó el micrófono mientras Vloomy hablaba. */
    private fun vaciar(grabador: AudioRecord) {
        val basura = ShortArray(WakeWord.BLOQUE)
        while (grabador.read(basura, 0, basura.size, AudioRecord.READ_NON_BLOCKING) > 0) Unit
    }

    private fun decir(frase: String) {
        tts.speak(frase, TextToSpeech.QUEUE_ADD, null, "v${utterance++}")
    }

    private fun esperarVoz() {
        Thread.sleep(300)
        while (tts.isSpeaking) Thread.sleep(100)
    }

    private fun avisar(texto: String) {
        getSystemService(NotificationManager::class.java).notify(1, notificacion(texto))
    }

    private fun notificacion(texto: String): Notification {
        val abrir = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, CANAL)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("Vloomy")
            .setContentText(texto)
            .setContentIntent(abrir)
            .setOngoing(true)
            .build()
    }

    companion object {
        const val HABLAR = "com.vloomy.HABLAR"
        private const val CANAL = "escucha"
        private const val TAG = "Vloomy"
        private const val VAD_UMBRAL = 0.5f
        private const val SILENCIO_FIN = 10   // ~0,8 s callado = terminaste de hablar
        private const val ESPERA_MAX = 62     // ~5 s sin que digas nada = falsa alarma
        private const val HABLA_MAX = 190     // ~15 s como máximo por pedido
    }
}
