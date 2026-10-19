package com.vloomy.wake

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Mismos WAV que puntuó Python: "hey_jarvis.wav" dio 0,998 y "frase_comun.wav" dio 0,000. */
class WakeWordTest {
    private fun wav(nombre: String) = Wav.leer(javaClass.getResourceAsStream("/$nombre")!!.use { it.readBytes() })

    private fun maximo(nombre: String): Float = WakeWord(listOf(WakeWord.recurso("hey_jarvis_v0.1.onnx"))).use { w ->
        wav(nombre).toList().chunked(WakeWord.BLOQUE).filter { it.size == WakeWord.BLOQUE }
            .maxOf { w.procesar(it.toShortArray())[0] }
    }

    @Test
    fun detectaHeyJarvis() {
        val puntaje = maximo("hey_jarvis.wav")
        println("hey_jarvis.wav -> $puntaje")
        assertTrue("puntaje $puntaje", puntaje > 0.9f)
    }

    @Test
    fun ignoraUnaFraseComun() {
        val puntaje = maximo("frase_comun.wav")
        println("frase_comun.wav -> $puntaje")
        assertTrue("puntaje $puntaje", puntaje < 0.1f)
    }

    @Test
    fun vadDistingueVozDeSilencio() = Vad().use { vad ->
        val voz = wav("frase_comun.wav").toList().chunked(1280).filter { it.size == 1280 }
            .maxOf { vad.probabilidad(it.toShortArray()) }
        vad.reset()
        val silencio = vad.probabilidad(ShortArray(1280))
        println("vad voz=$voz silencio=$silencio")
        assertTrue(voz > 0.5f && silencio < 0.2f)
    }

    @Test
    fun wavIdaYVuelta() {
        val pcm = shortArrayOf(0, 1, -1, Short.MAX_VALUE, Short.MIN_VALUE)
        val bytes = Wav.aBytes(pcm)
        assertEquals(44 + pcm.size * 2, bytes.size)
        assertEquals("RIFF", String(bytes, 0, 4))
        assertEquals("WAVE", String(bytes, 8, 4))
        assertArrayEquals(pcm, Wav.leer(bytes))
    }
}
