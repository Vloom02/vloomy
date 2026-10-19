package com.vloomy

import com.vloomy.wake.Wav
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Cliente del servidor de la PC (voice/vloomy.py). Protocolo en GUIA.md. */
class Servidor(private val base: String, private val token: String) {

    fun salud(): String {
        val c = conexion("/salud")
        return when (val codigo = c.responseCode) {
            200 -> "Conectado con la PC."
            401 -> "La PC respondió, pero el token no coincide."
            else -> "La PC respondió con error $codigo."
        }
    }

    /** Manda el pedido y llama a [alEvento] con cada línea del NDJSON a medida que llega. */
    fun voz(audio: ShortArray, alEvento: (JSONObject) -> Unit) {
        val c = enviar("/voz", audio)
        if (c.responseCode != 200) error("la PC respondió ${c.responseCode}")
        c.inputStream.bufferedReader().useLines { lineas ->
            lineas.filter { it.isNotBlank() }.forEach { alEvento(JSONObject(it)) }
        }
    }

    fun responder(id: String, audio: ShortArray) {
        enviar("/responder/$id", audio).responseCode
    }

    private fun enviar(ruta: String, audio: ShortArray): HttpURLConnection {
        val cuerpo = Wav.aBytes(audio)
        return conexion(ruta).apply {
            requestMethod = "POST"
            doOutput = true
            setRequestProperty("Content-Type", "audio/wav")
            setFixedLengthStreamingMode(cuerpo.size)
            outputStream.use { it.write(cuerpo) }
        }
    }

    private fun conexion(ruta: String) =
        (URL(base.trim().trimEnd('/') + ruta).openConnection() as HttpURLConnection).apply {
            connectTimeout = 5_000
            readTimeout = 90_000
            setRequestProperty("Authorization", "Bearer ${token.trim()}")
        }
}
