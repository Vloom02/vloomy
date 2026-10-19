package com.vloomy.wake

import java.nio.ByteBuffer
import java.nio.ByteOrder

/** WAV mono 16 kHz de 16 bits: el formato que espera el servidor de la PC en /voz. */
object Wav {
    const val TASA = 16000

    fun aBytes(pcm: ShortArray): ByteArray {
        val datos = pcm.size * 2
        return ByteBuffer.allocate(44 + datos).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RIFF".toByteArray()); putInt(36 + datos); put("WAVE".toByteArray())
            put("fmt ".toByteArray()); putInt(16); putShort(1); putShort(1)  // PCM, mono
            putInt(TASA); putInt(TASA * 2); putShort(2); putShort(16)        // byte rate, block align, bits
            put("data".toByteArray()); putInt(datos)
            pcm.forEach { putShort(it) }
        }.array()
    }

    fun leer(bytes: ByteArray): ShortArray {
        val pcm = ByteBuffer.wrap(bytes, 44, bytes.size - 44).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        return ShortArray(pcm.remaining()).also { pcm.get(it) }
    }
}
