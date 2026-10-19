package com.vloomy.wake

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Mismos WAV que puntuó Python: "hey_jarvis.wav" dio 0,998 y "frase_comun.wav" dio 0,000. */
class WakeWordTest {
    private fun wav(nombre: String) = Wav.leer(javaClass.getResourceAsStream("/$nombre")!!.use { it.readBytes() })

    /** Puntajes bloque a bloque de cada modelo incluido (hey jarvis y, si está, hey vloomy). */
    private fun puntajes(nombre: String): List<FloatArray> =
        WakeWord(WakeWord.incluidos().map { it.first }).use { w ->
            wav(nombre).toList().chunked(WakeWord.BLOQUE).filter { it.size == WakeWord.BLOQUE }
                .map { w.procesar(it.toShortArray()) }
        }

    /** Máximo de bloques seguidos arriba del umbral (la app se activa con 2). */
    private fun seguidos(p: List<FloatArray>, modelo: Int): Int {
        val umbral = WakeWord.incluidos()[modelo].second
        var actual = 0
        var maximo = 0
        for (b in p) {
            actual = if (b[modelo] >= umbral) actual + 1 else 0
            maximo = maxOf(maximo, actual)
        }
        return maximo
    }

    @Test
    fun detectaHeyJarvis() {
        val p = puntajes("hey_jarvis.wav")
        println("hey_jarvis.wav -> máximo ${p.maxOf { it[0] }}, seguidos ${seguidos(p, 0)}")
        assertTrue(p.maxOf { it[0] } > 0.9f)
        assertTrue(seguidos(p, 0) >= 2)
    }

    @Test
    fun detectaHeyVloomy() {
        if (WakeWord.incluidos().size < 2) return  // todavía sin modelo propio
        val p = puntajes("hey_blumi.wav")
        println("hey_blumi.wav -> máximo ${p.maxOf { it[1] }}, seguidos ${seguidos(p, 1)}")
        assertTrue(seguidos(p, 1) >= 2)
    }

    @Test
    fun ignoraUnaFraseComun() {
        val p = puntajes("frase_comun.wav")
        println("frase_comun.wav -> máximos ${p.first().indices.map { i -> p.maxOf { it[i] } }}")
        for (i in p.first().indices) assertTrue(seguidos(p, i) < 2)
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
