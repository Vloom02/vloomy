package com.vloomy.wake

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer

/** Silero VAD (el mismo modelo y cálculo que openwakeword/vad.py): probabilidad de que haya voz. */
class Vad : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val sesion = env.createSession(WakeWord.recurso("silero_vad.onnx"), OrtSession.SessionOptions().apply {
        setIntraOpNumThreads(1)
        setInterOpNumThreads(1)
    })
    private var h = FloatArray(2 * 64)
    private var c = FloatArray(2 * 64)

    fun reset() {
        h = FloatArray(2 * 64)
        c = FloatArray(2 * 64)
    }

    /** Promedio de voz en el bloque (múltiplo de 640 muestras, como en Python). */
    fun probabilidad(bloque: ShortArray): Float {
        var suma = 0f
        val trozos = bloque.size / TROZO
        for (t in 0 until trozos) {
            val entrada = FloatArray(TROZO) { bloque[t * TROZO + it] / 32767f }
            val tensores = mapOf(
                "input" to OnnxTensor.createTensor(env, FloatBuffer.wrap(entrada), longArrayOf(1, TROZO.toLong())),
                "sr" to OnnxTensor.createTensor(env, 16000L),
                "h" to OnnxTensor.createTensor(env, FloatBuffer.wrap(h), longArrayOf(2, 1, 64)),
                "c" to OnnxTensor.createTensor(env, FloatBuffer.wrap(c), longArrayOf(2, 1, 64)),
            )
            sesion.run(tensores).use { r ->
                suma += leer(r[0] as OnnxTensor)[0]
                h = leer(r[1] as OnnxTensor)
                c = leer(r[2] as OnnxTensor)
            }
            tensores.values.forEach { it.close() }
        }
        return suma / trozos
    }

    private fun leer(t: OnnxTensor): FloatArray = t.floatBuffer.let { b -> FloatArray(b.remaining()).also { b.get(it) } }

    override fun close() = sesion.close()

    companion object {
        private const val TROZO = 640
    }
}
