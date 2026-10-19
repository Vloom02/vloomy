package com.vloomy.wake

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer

/**
 * openWakeWord en Kotlin: el mismo cálculo que utils.AudioFeatures + Model.predict de Python.
 * Recibe bloques de 1280 muestras (80 ms a 16 kHz, PCM 16 bits) y devuelve un puntaje de 0 a 1.
 */
class WakeWord(modelo: ByteArray) : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val opciones = OrtSession.SessionOptions().apply {
        setIntraOpNumThreads(1)
        setInterOpNumThreads(1)
    }
    private val melSesion = env.createSession(recurso("melspectrogram.onnx"), opciones)
    private val embSesion = env.createSession(recurso("embedding_model.onnx"), opciones)
    private val wakeSesion = env.createSession(modelo, opciones)
    private val wakeEntrada = wakeSesion.inputNames.first()

    private val crudo = ShortArray(CONTEXTO + BLOQUE)  // el bloque nuevo + 3 frames de contexto
    private val mel = ArrayDeque<FloatArray>()
    private val features = ArrayDeque<FloatArray>()
    private var predicciones = 0

    init {
        reset()
    }

    fun reset() {
        crudo.fill(0)
        mel.clear()
        repeat(VENTANA_MEL) { mel.addLast(FloatArray(MEL_BINS) { 1f }) }  // Python arranca con np.ones((76, 32))
        // Python llena el buffer con embeddings de 10 s de silencio: todos iguales, así que alcanza con uno.
        val silencio = melspec(ShortArray(CONTEXTO + BLOQUE)).first()
        val vacio = embedding(List(VENTANA_MEL) { silencio })
        features.clear()
        repeat(FEATURES_MODELO) { features.addLast(vacio) }
        predicciones = 0
    }

    fun procesar(bloque: ShortArray): Float {
        require(bloque.size == BLOQUE) { "el bloque tiene que tener $BLOQUE muestras" }
        System.arraycopy(crudo, BLOQUE, crudo, 0, CONTEXTO)
        System.arraycopy(bloque, 0, crudo, CONTEXTO, BLOQUE)
        for (frame in melspec(crudo)) {
            mel.addLast(frame)
            if (mel.size > MEL_MAX) mel.removeFirst()
        }
        features.addLast(embedding(mel.toList().takeLast(VENTANA_MEL)))
        if (features.size > FEATURES_MAX) features.removeFirst()
        val puntaje = predecir(features.toList().takeLast(FEATURES_MODELO))
        return if (predicciones++ < 5) 0f else puntaje  // Python ignora las primeras 5 predicciones
    }

    private fun melspec(muestras: ShortArray): List<FloatArray> {
        val entrada = FloatArray(muestras.size) { muestras[it].toFloat() }
        val salida = correr(melSesion, "input", entrada, longArrayOf(1, muestras.size.toLong()))
        return salida.toList().chunked(MEL_BINS).map { frame -> FloatArray(MEL_BINS) { frame[it] / 10f + 2f } }
    }

    private fun embedding(ventana: List<FloatArray>): FloatArray {
        val entrada = FloatArray(VENTANA_MEL * MEL_BINS)
        ventana.forEachIndexed { i, frame -> frame.copyInto(entrada, i * MEL_BINS) }
        return correr(embSesion, "input_1", entrada, longArrayOf(1, VENTANA_MEL.toLong(), MEL_BINS.toLong(), 1))
    }

    private fun predecir(ventana: List<FloatArray>): Float {
        val entrada = FloatArray(FEATURES_MODELO * EMB_DIM)
        ventana.forEachIndexed { i, f -> f.copyInto(entrada, i * EMB_DIM) }
        return correr(wakeSesion, wakeEntrada, entrada, longArrayOf(1, FEATURES_MODELO.toLong(), EMB_DIM.toLong()))[0]
    }

    private fun correr(sesion: OrtSession, nombre: String, datos: FloatArray, forma: LongArray): FloatArray =
        OnnxTensor.createTensor(env, FloatBuffer.wrap(datos), forma).use { tensor ->
            sesion.run(mapOf(nombre to tensor)).use { r ->
                val buf = (r[0] as OnnxTensor).floatBuffer
                FloatArray(buf.remaining()).also { buf.get(it) }
            }
        }

    override fun close() {
        melSesion.close()
        embSesion.close()
        wakeSesion.close()
    }

    companion object {
        const val BLOQUE = 1280
        private const val CONTEXTO = 480       // 160 * 3, igual que Python
        private const val MEL_BINS = 32
        private const val VENTANA_MEL = 76
        private const val MEL_MAX = 970        // 10 s de frames
        private const val EMB_DIM = 96
        private const val FEATURES_MODELO = 16
        private const val FEATURES_MAX = 120

        fun recurso(nombre: String): ByteArray =
            WakeWord::class.java.getResourceAsStream("/models/$nombre")?.use { it.readBytes() }
                ?: error("falta el modelo $nombre")
    }
}
