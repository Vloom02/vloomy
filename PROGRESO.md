# Vloomy: progreso y traspaso

Archivo para retomar el trabajo desde una sesión nueva (por ejemplo, si se cortan los tokens).
**Si este archivo se modificó hace menos de 45 minutos, hay otra sesión trabajando: no tocar nada.**

## Pedido del usuario (19/10/2026, madrugada)

"Jarvis" propio llamado **Vloomy**, manos libres, en **PC (Windows) y Android**. Para la mañana tiene que quedar
listo para pruebas reales. El usuario autorizó instalar todo lo necesario y seguir sin consultarle.

Restricciones:
- **Costo cero extra.** Groq gratis (clave en `.env`), modelos locales y suscripción de Claude solo vía Claude Code oficial.
- **Todo en el disco D**, dentro de `D:\Claude\repos\vloomy`: herramientas en `.tools`, modelos en `.cache`, Python en `.uv`.
- Español rioplatense en código, textos y respuestas.
- `.env` **nunca** se sube (tiene `GROQ_API_KEY` y `VLOOMY_TOKEN`).
- Repo privado: https://github.com/Vloom02/vloomy. Hacer push después de cada etapa.
- Nada de cambios de sistema: firewall, Modo desarrollador, servicios ni Tailscale los hace el usuario.

## Estado

- [x] Fase 1 PC: wake word "hey jarvis", VAD, voz a texto (Groq whisper-large-v3-turbo, respaldo faster-whisper small), capa 0, capa 1 (Groq gpt-oss-120b → gpt-oss-20b → Ollama qwen2.5:3b), voz Kokoro fp32 `em_alex` es-419.
- [x] Abrir apps sin Windows-MCP (`capa0.abrir_app`: Get-StartApps + `shell:AppsFolder`). Windows-MCP solo para `Shortcut` (con confirmación) y `App` switch/resize.
- [x] Servidor HTTP para el celular dentro de `voice/vloomy.py` (ver protocolo abajo). Probado con `voice/prueba.py`.
- [x] Repo privado creado y subido.
- [x] Herramientas Android portables en `D:\Claude\repos\vloomy\.tools`: JDK 21, Android SDK 35, Gradle 8.11.1 (wrapper en `android/`). Gradle usa `.tools\gradle-home`.
- [x] App Android en `android/` (APK en `Vloomy.apk`, se recompila con `android\build.cmd`).
- [x] Test JVM del wake word en Kotlin: 0,9978 contra 0,998 de Python con el mismo WAV.
- [x] Capa 2: `delegar_a_claude` corre `claude.exe -p --output-format json` sin ventana en `capa2/` (tarea por stdin) y avisa el resultado por voz. Reemplazó al canal (`--dangerously-load-development-channels` pedía confirmar en cada arranque). Requiere una vez `capa2.cmd`: iniciar sesión y confiar en la carpeta.
- [x] Modo conversación (~7 s sin palabra después de cada respuesta) en PC y celular; "gracias/listo/chau" cortan.
- [x] `vloomy.log` en la raíz con lo que muestra la ventana (se pisa en cada arranque).
- [x] "Hey Vloomy" entrenado (`voice\modelos\hey_vloomy.onnx` + `.json`, umbral 0,55, paciencia 2): 99,5% de detección en vivo con voces nuevas y 0 falsas/hora en 10,7 h reales. Copiado a la app. "Hey Jarvis" sigue activo. Negativos en `.cache\wake` (ACAV100M 16 GB + validación).
- [x] Herramienta `calcular` (cuenta exacta con ast): gpt-oss-120b erraba cuentas en palabras.
- [x] GUIA.md completa con los pasos para la mañana.

## Pendiente (necesita al usuario o un teléfono)

- Probar con micrófono real en la PC y en el celular. Ajustar umbrales con su voz si hace falta.
- ~~Abrir `capa2.cmd` una vez: iniciar sesión y confiar en la carpeta.~~ Hecho el 20/10/2026: capa 2 probada sin ventana ("hola" en 10 s; búsqueda web en 20 s).
- Permitir Python en el firewall (lo pide Windows la primera vez que corre `vloomy.cmd`).
- Opcional: Tailscale para usarlo fuera de casa.

## Registro

- 19/10/2026 02:43: fases 1 a 4 terminadas y probadas sin micrófono (Python, JVM y protocolo del canal). APK compilado.
- 20/10/2026: el usuario probó en la PC (anda). Arreglos: un error de sonido trababa el loop; modo conversación; capa 2 sin ventana.

## Cómo probar

```powershell
cd D:\Claude\repos\vloomy\voice
.\.venv\Scripts\python.exe test_capa0.py   # comandos fijos, sin red
.\.venv\Scripts\python.exe prueba.py       # punta a punta sin micrófono (usa Groq)
```

Para usar `uv` desde la app de Claude (MSIX virtualiza AppData), primero cargar las variables de `uv-env.ps1`
(UV_PYTHON_INSTALL_DIR, UV_CACHE_DIR, UV_TOOL_DIR, UV_TOOL_BIN_DIR dentro de `.uv`, UV_PYTHON_PREFERENCE=only-managed).

## Protocolo PC ↔ celular

Todas las rutas exigen el header `Authorization: Bearer <VLOOMY_TOKEN>` (está en `.env`). Si falta, se genera solo.
Puerto 8765 en 0.0.0.0. Se cambian con `VLOOMY_HOST` y `VLOOMY_PUERTO`.

| Ruta | Envío | Respuesta |
|---|---|---|
| `GET /salud` | — | `{"ok": true, "nombre": "Vloomy"}` |
| `POST /voz` | WAV mono 16 kHz 16 bits con el pedido, ya recortado | NDJSON, una línea por evento: `{"vos": texto}`, `{"decir": frase}`…, `{"preguntar": "¿Confirmo…?", "id": "abcd1234"}`, y por último `{"fin": true}` |
| `POST /responder/{id}` | WAV con la respuesta a una confirmación | `{"ok": true, "texto": "..."}` |

Cuando llega `preguntar`, la app lo dice, graba la respuesta y la manda a `/responder/{id}` mientras sigue leyendo
el mismo stream de `/voz`.

## Diseño de la app Android

- Kotlin, sin Compose ni AndroidX salvo lo mínimo. minSdk 29 y target/compileSdk 35.
- `WakeWord.kt` en Kotlin puro, testeable en la JVM con onnxruntime de escritorio. Es el port de `openwakeword/utils.py`:
  melspectrogram.onnx → (x/10)+2 → ventanas de 76 frames de mel con paso 8 → embedding_model.onnx → últimas 16 → hey_jarvis_v0.1.onnx.
  Los modelos se copian de `voice\.venv\Lib\site-packages\openwakeword\resources\models` a `assets`.
- Servicio en primer plano `microphone` con notificación fija y wake lock parcial. Después del wake: bip, grabación con
  VAD Silero (silero_vad.onnx, entradas input/h/c/sr), POST /voz, TextToSpeech es-AR frase por frase.
- Pantalla: URL de la PC, token, botones "Activar escucha", "Probar conexión" y "Hablar" (push-to-talk).
- Android 14+: el servicio de micrófono no puede arrancar desde BOOT_COMPLETED; se activa desde la app.
