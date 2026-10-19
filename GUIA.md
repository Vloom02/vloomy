# Vloomy: guía (fase 1, PC)

Asistente por voz para tu PC, estilo Jarvis, **sin pagar nada extra**. Todo vive en
`D:\Claude\repos\vloomy`: código, modelos, cachés y Ollama.

## Cómo se usa

1. Doble clic en **`vloomy.cmd`**. Espera a que diga "Vloomy listo".
2. Decí **"Hey Jarvis"**, en inglés ("jéi yárvis"). Suena un **bip**.
3. Pedí lo que quieras y callate: a los ~0,8 s de silencio responde.

"Hey Jarvis" es provisorio hasta entrenar "Hey Vloomy" (fase 3).

### Qué le podés pedir

| Tipo | Ejemplos | Quién lo resuelve |
|---|---|---|
| Comandos fijos | "abrí Spotify", "subí / bajá el volumen", "silencio", "pausá la música", "siguiente canción", "¿qué hora es?", "¿qué día es hoy?", "bloqueá la compu" | **Capa 0** (sin IA, en milisegundos) |
| Cualquier otra cosa | "poné la música un poco más fuerte", "abrí la calculadora y el bloc de notas", "¿cuál es la capital de Australia?", "cerrá esta ventana" | **Capa 1** (IA gratis con herramientas) |

Los **atajos de teclado** ("cerrá esta ventana" → `alt+f4`) te preguntan "¿Confirmo…?".
Contestás "sí", "dale" u "ok"; cualquier otra cosa lo cancela.

## Cómo funciona

```
micrófono ─▶ wake word (local) ─▶ bip ─▶ graba hasta que te callás (VAD local)
          ─▶ voz a texto: Groq whisper-large-v3-turbo  (si falla: Whisper local)
          ─▶ capa 0: ¿es un comando fijo?  sí ─▶ lo ejecuta
                                          no ─▶ capa 1: IA con herramientas
                                                Groq  (si falla o se agota: Ollama local en tu GPU)
          ─▶ respuesta en voz (Kokoro local), frase por frase
```

| Pieza | Qué hace | Dónde corre | Costo |
|---|---|---|---|
| **openWakeWord** 0.4 (`hey_jarvis`) | Detecta la palabra de activación | Tu PC | $0 |
| **Silero VAD** (viene con openWakeWord) | Detecta cuándo empezás y terminás de hablar | Tu PC | $0 |
| **Groq whisper-large-v3-turbo** | Voz a texto, rápido y preciso | Nube (gratis) | $0 |
| **faster-whisper `small`** | Respaldo de voz a texto | Tu PC (CPU) | $0 |
| **capa0.py** | Comandos fijos sin IA | Tu PC | $0 |
| **Groq `{{GROQ_LLM}}`** | Entiende pedidos libres y decide qué herramienta usar | Nube (gratis) | $0 |
| **Ollama `{{OLLAMA_LLM}}`** | Respaldo local si Groq falla | Tu GTX 1650 | $0 |
| **Windows-MCP** 0.8.8 | Abre y cambia apps, hace atajos de teclado | Tu PC | $0 |
| **Kokoro** v1.0 (`em_alex`, español latino) | Texto a voz | Tu PC (CPU) | $0 |

### Dónde está cada cosa (todo en D)

| Carpeta / archivo | Contenido |
|---|---|
| `vloomy.cmd` | Arranque |
| `voice\vloomy.py` | El asistente |
| `voice\capa0.py` + `test_capa0.py` | Comandos fijos y su test |
| `.env` | Tu clave de Groq (no se sube a git) |
| `.cache\kokoro` | Voz (337 MB) |
| `.cache\huggingface` | Whisper de respaldo (464 MB) |
| `.cache\ollama` | Modelos locales |
| `.tools\ollama` | Ollama portable (no se instaló en C) |
| `.uv` | Python y Windows-MCP |

## Seguridad

- **Herramientas en lista blanca:** solo `App` (abrir, cambiar o redimensionar ventanas) y `Shortcut` (atajos), más volumen, música, hora y bloqueo.
- **El modo `launch_executable` está bloqueado:** permitiría correr cualquier programa con argumentos.
- **Los atajos piden confirmación por voz.**
- **Qué viaja a Groq:** el audio y el texto de lo que pedís **después** del "Hey Jarvis", y lo que devuelven las herramientas. Nada antes de la palabra de activación. Según fuentes de terceros, Groq no entrena con datos de la API.
- **Lo que devuelven las herramientas es información, no órdenes** (regla en el prompt del sistema).

## Mediciones (sin micrófono, voz sintética)

{{MEDICIONES}}

## Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| No reacciona al "Hey Jarvis" | Decilo en inglés y claro. Revisá en Configuración → Privacidad → Micrófono que esté permitido para apps de escritorio. Si aun así no reacciona, bajá `WAKE_UMBRAL` en `vloomy.py` (0.5 → 0.3). |
| Se activa solo | Subí `WAKE_UMBRAL` (0.5 → 0.7). |
| Corta antes de que termines | Subí `SILENCIO_FIN` (10 = 0,8 s → 15 = 1,2 s). |
| Dice "[ia] … falló" | Groq sin cupo o sin internet: pasa solo a Ollama local. La primera vez tarda en cargar el modelo en la GPU. |
| "No pude conectarme con ningún modelo" | Sin internet y Ollama apagado. Cerrá y volvé a abrir `vloomy.cmd` (lo levanta solo). |

## Comandos útiles

```powershell
# Test de la capa 0
cd D:\Claude\repos\vloomy\voice; .\.venv\Scripts\python.exe test_capa0.py

# Arrancar Vloomy desde la terminal
D:\Claude\repos\vloomy\vloomy.cmd
```

## Próximas fases

| Fase | Qué |
|---|---|
| 2 | **Capa 2:** tareas pesadas con tu suscripción de Claude, mediante un canal propio hacia Claude Code, con "lo hago y te aviso" y aprobación por voz. |
| 3 | Entrenar **"Hey Vloomy"** y ajustarlo con tu voz. |
| 4 | **App Android** con wake word, voz en el celular y conexión a la PC por Tailscale. |
