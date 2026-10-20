package com.vloomy

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlin.concurrent.thread

/** Configuración mínima: dirección de la PC, token, y prender o apagar la escucha. */
class MainActivity : Activity() {
    private lateinit var url: EditText
    private lateinit var token: EditText
    private lateinit var estado: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        url = EditText(this).apply {
            hint = "http://192.168.0.10:8765"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setText(prefs.getString("url", ""))
        }
        token = EditText(this).apply {
            hint = "Token (lo muestra la PC al arrancar Vloomy)"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
            setText(prefs.getString("token", ""))
        }
        estado = TextView(this).apply { text = "Con la escucha activa, decí \"Hey Vloomy\" (o \"Hey Jarvis\")." }

        val columna = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 64, 48, 48)
            addView(TextView(this@MainActivity).apply { text = "Vloomy"; textSize = 28f })
            addView(etiqueta("Dirección de la PC"))
            addView(url)
            addView(etiqueta("Token"))
            addView(token)
            addView(boton("Guardar y probar conexión") { probar() })
            addView(boton("Activar escucha") { servicio(null) })
            addView(boton("Hablar ahora") { servicio(VloomyService.HABLAR) })
            addView(boton("Detener escucha") { stopService(Intent(this@MainActivity, VloomyService::class.java)) })
            addView(boton("Que no la corte el ahorro de batería") { sinAhorro() })
            addView(estado)
        }
        setContentView(ScrollView(this).apply { addView(columna) })

        val permisos = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) permisos += Manifest.permission.POST_NOTIFICATIONS
        requestPermissions(permisos.toTypedArray(), 1)
    }

    private fun guardar() = getSharedPreferences(PREFS, MODE_PRIVATE).edit()
        .putString("url", url.text.toString().trim())
        .putString("token", token.text.toString().trim())
        .apply()

    private fun probar() {
        guardar()
        estado.text = "Probando…"
        thread {
            val r = runCatching { Servidor(url.text.toString(), token.text.toString()).salud() }
                .getOrElse { "No llego a la PC: ${it.message}" }
            runOnUiThread { estado.text = r }
        }
    }

    private fun servicio(accion: String?) {
        guardar()
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            estado.text = "Falta el permiso de micrófono."
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 1)
            return
        }
        startForegroundService(Intent(this, VloomyService::class.java).setAction(accion))
        estado.text = if (accion == null) "Escuchando. Decí \"Hey Vloomy\"." else "Te escucho…"
    }

    private fun sinAhorro() {
        startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")))
    }

    private fun etiqueta(texto: String) = TextView(this).apply { text = texto; setPadding(0, 32, 0, 0) }

    private fun boton(texto: String, accion: () -> Unit) = Button(this).apply {
        text = texto
        setOnClickListener { accion() }
    }

    companion object {
        const val PREFS = "vloomy"
    }
}
