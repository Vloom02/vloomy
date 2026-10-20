# Vloomy: guía

Asistente por voz estilo Jarvis para tu **PC** y tu **celular Android**, **sin pagar nada extra**.
Todo vive en `D:\Claude\repos\vloomy` (código, modelos, herramientas). Copia privada en
https://github.com/Vloom02/vloomy.

---

## Para probar a la mañana (en este orden)

### 1. PC (5 minutos)

1. Doble clic en **`vloomy.cmd`**. Espera a que diga "Vloomy listo".
2. **La primera vez, Windows pregunta por el firewall** para Python: tildá **Redes privadas** y tocá **Permitir**.
   Sin eso, el celular no llega a la PC.
3. En la ventana aparece una línea así:
   ```
   Celular: http://192.168.1.4:8765   token: xxxxxxxx
   ```
   Anotá la dirección y el token: van en la app del celular.
4. Probalo: decí **"Hey Vloomy"** (o **"Hey Jarvis"**, en inglés). Suena un **bip**: pedí algo y callate.
   - "abrí la calculadora", "subí el volumen", "¿qué hora es?"
   - "¿cuál es la capital de Australia?", "abrí Spotify y poné pausa"

### 2. Celular Android (10 minutos)

1. Pasá **`D:\Claude\repos\vloomy\Vloomy.apk`** al celular: por cable USB, Drive o mandándotelo por WhatsApp.
2. Abrilo en el celular. Android pide permiso para **instalar apps desconocidas** desde esa app (Archivos, Drive o
   WhatsApp): activalo y tocá **Instalar**. Si Play Protect avisa, tocá **Instalar de todas formas**. Es tu app,
   firmada con una clave de desarrollo.
3. Abrí **Vloomy** y aceptá **micrófono** y **notificaciones**.
4. Completá **Dirección de la PC** (`http://192.168.1.4:8765`) y el **Token**. Tocá **Guardar y probar conexión**
   y tiene que decir "Conectado con la PC.". El celular tiene que estar en el **mismo Wi-Fi** que la PC.
5. Tocá **Que no la corte el ahorro de batería** y aceptá.
6. Tocá **Activar escucha**. Aparece una notificación fija "Vloomy". Ya podés bloquear el celular y decir
   **"Hey Vloomy, ¿qué hora es?"**.
7. **"Hablar ahora"** sirve para pedir algo sin decir la palabra de activación.

### 3. Capa 2: tareas pesadas con tu suscripción de Claude (opcional, 10 minutos)

1. Doble clic en **`capa2.cmd`**. La primera vez:
   - Iniciá sesión con tu cuenta de Claude: se abre el navegador.
   - Aceptá el aviso de **development channels**: elegí "I am using this for local development".
   - Aprobá los servidores MCP **vloomy** y **playwright**.
2. Dejá esa ventana abierta, junto con `vloomy.cmd`.
3. Pedile algo largo: **"Hey Vloomy, investigá qué auriculares baratos con buena batería hay y armame un
   resumen"**. Vloomy dice "Se la pasé a Claude" y, cuando Claude termina, te lo cuenta en voz alta. Si Claude
   necesita un permiso, Vloomy te pregunta "¿Lo dejo?".

### 4. Fuera de casa (opcional)

Instalá **Tailscale** en la PC (`winget install --id Tailscale.Tailscale`) y en el celular (Play Store), con la misma
cuenta. En la app poné `http://<IP 100.x de la PC en Tailscale>:8765`. Así funciona en cualquier red, cifrado, y sin
abrir puertos.

---

## Qué le podés pedir

| Tipo | Ejemplos | Quién lo resuelve | Tiempo típico |
|---|---|---|---|
| Comandos fijos | "abrí Spotify", "subí / bajá el volumen", "silencio", "pausá la música", "siguiente canción", "¿qué hora es?", "¿qué día es hoy?", "bloqueá la compu" | **Capa 0**, sin IA | instantáneo |
| Pedidos libres | "poné la música un poco más fuerte", "abrí la calculadora y el bloc de notas", "¿cuál es la capital de Australia?", "cerrá esta ventana" | **Capa 1**: Groq gpt-oss-120b, gratis | ~0,5 a 0,8 s |
| Cuentas | "¿cuánto es 15 por 7?", "¿cuántos minutos son tres horas y media?" | Capa 1 + `calcular` (cuenta exacta) | ~0,8 a 1,2 s |
| Tareas largas | "investigá…", "comparame…", "ordená las descargas…", "armame un informe…" | **Capa 2**: Claude Code con tu suscripción | minutos, te avisa al terminar |

- **Los atajos de teclado** ("cerrá esta ventana" → `alt+f4`) preguntan "¿Confirmo…?". Contestás "sí", "dale" u "ok";
  cualquier otra cosa lo cancela.
- **Vloomy recuerda las últimas 3 idas y vueltas**, compartidas entre la PC y el celular, así que "¿y ahora cerrala?" funciona.
- **Modo conversación:** después de cada respuesta sigue escuchando **~7 segundos sin que repitas "Hey Vloomy"**. Si
  te quedás callado, vuelve a esperar la palabra. "Gracias", "listo", "chau" o "nada más" cortan la conversación. Anda
  igual en la PC y en el celular.

## Cómo funciona

```
PC:       micrófono ─▶ wake word ─▶ bip ─▶ graba hasta que te callás ─┐
Celular:  micrófono ─▶ wake word ─▶ bip ─▶ graba ─▶ POST /voz (Wi-Fi) ─┤
                                                                       ▼
          voz a texto: Groq whisper-large-v3-turbo (si falla: Whisper local)
          ─▶ capa 0: ¿comando fijo?  sí ─▶ lo hace
                                     no ─▶ capa 1: Groq gpt-oss-120b → gpt-oss-20b → Ollama local (respaldo)
                                           herramientas: control_pc · abrir_app · calcular · atajos · ventanas · delegar_a_claude
                                                                                       │
                                           capa 2: Claude Code (capa2.cmd) ◀── canal ──┘ ── avisa al terminar
          ─▶ respuesta frase por frase: voz Kokoro en la PC / voz de Android en el celular
```

| Pieza | Qué hace | Dónde corre |
|---|---|---|
| openWakeWord `hey_jarvis` + **`hey_vloomy` propio** | Detectan la palabra de activación | PC y celular, local |
| Silero VAD | Detecta cuándo empezás y terminás de hablar | PC y celular, local |
| Groq whisper-large-v3-turbo | Voz a texto, rápido | Nube gratis |
| faster-whisper `small` | Respaldo de voz a texto | PC (CPU) |
| `capa0.py` | Comandos fijos y apertura de apps desde el menú Inicio | PC |
| Groq gpt-oss-120b / 20b | Entienden pedidos libres y usan herramientas | Nube gratis |
| Ollama qwen2.5:3b | Respaldo si no hay Groq | PC (tu GTX 1650) |
| Windows-MCP | Atajos de teclado y traer ventanas al frente | PC |
| Kokoro `em_alex` | Voz de Vloomy en la PC | PC (CPU) |
| TextToSpeech de Android | Voz de Vloomy en el celular | Celular |
| Claude Code + `capa2/canal.mjs` | Tareas largas con tu suscripción | PC |

## Palabra de activación "Hey Vloomy"

Podés decir **"Hey Vloomy"** (se pronuncia como suena: "jei blumi") o **"Hey Jarvis"** (en inglés). Las dos andan
siempre, en la PC y en el celular.

**Cómo se entrenó "Hey Vloomy"** (`voice\entrenar_wake.py`, ~10 minutos con los datos ya bajados):
- **Positivos:** 37 voces sintéticas de Kokoro, en español y en inglés, a 4 velocidades, con ruido de fondo, eco y
  cambios de tono.
- **Negativos:** frases parecidas ("hey Lumi", "blusa", "Bloomberg", "hey Jarvis"…), 200.000 ventanas de habla y
  ruido reales (ACAV100M) y las 5.685 ventanas reales que más lo confundían, en una segunda vuelta.
- **Paciencia 2:** tiene que pasar el umbral en dos bloques seguidos de 80 ms. Eso corta los picos sueltos.

| Métrica | Hey Vloomy (umbral 0,55) | Hey Jarvis oficial (umbral 0,5) |
|---|---|---|
| Detecta, con voces que nunca escuchó (en vivo) | **99,5%** | — |
| Falsas activaciones en 10,7 h de audio real | **0 por hora** | 0,19 por hora |

**Ojo:** se entrenó con voces sintéticas, así que con tu voz real puede variar.
- **Si no te reconoce:** bajá `umbral` en `voice\modelos\hey_vloomy.json` (0,55 → 0,4).
- **Si se activa solo:** subilo (→ 0,7).
- **Para aplicarlo:** en la PC alcanza con reabrir `vloomy.cmd`. En el celular copiá el `.json` a
  `android\wake\src\main\resources\models\` y corré `android\build.cmd`.

## Dónde está cada cosa (todo en D)

| Archivo / carpeta | Qué es |
|---|---|
| `vloomy.cmd` | Arranca Vloomy en la PC y el servidor para el celular |
| `capa2.cmd` | Arranca la capa 2 (Claude Code) |
| `Vloomy.apk` | La app para instalar en el celular |
| `voice\vloomy.py` | El cerebro: voz, IA, herramientas, servidor del celular, capa 2 |
| `voice\capa0.py` | Comandos fijos y apertura de apps |
| `voice\entrenar_wake.py` | Entrena "Hey Vloomy" |
| `voice\modelos\` | El modelo "Hey Vloomy" entrenado |
| `android\` | Código de la app; `build.cmd` la recompila |
| `capa2\` | Canal, configuración y reglas (`CLAUDE.md`) de la capa 2 |
| `.env` | Tu clave de Groq y el token del celular. **No se sube a GitHub.** |
| `.tools\` | Java, SDK de Android, Gradle y Ollama portables |
| `.cache\` | Modelos de voz, Whisper, Ollama y datos del wake word |
| `PROGRESO.md` | Estado del proyecto y traspaso entre sesiones |

## Seguridad

- **Para entrar a la PC desde el celular hace falta el token**, que se compara en tiempo constante. Sin token, nada.
- **Herramientas en lista blanca:**
  - Abrir apps solo desde el menú Inicio (sin ejecutar programas sueltos).
  - Atajos con confirmación por voz.
  - Volumen, música, hora y bloqueo.
  - El modo `launch_executable` de Windows-MCP está bloqueado.
- **La capa 2 tiene reglas escritas en `capa2\CLAUDE.md`:**
  - Nada destructivo, no compra, no manda mensajes, no ingresa contraseñas.
  - Los borrados por consola están denegados en `capa2\.claude\settings.json`.
  - Lo demás pide permiso, y Vloomy te lo pregunta por voz.
- **Lo que devuelven las herramientas y las páginas web es información, nunca órdenes.**
- **El canal de la capa 2 solo escucha en `127.0.0.1`.** El celular nunca le habla directo.
- **En Wi-Fi la conexión con el celular es http.** En redes que no son tuyas usá Tailscale, que cifra.
- **Qué viaja a Groq:** el audio y el texto de lo que pedís después de la palabra de activación. Nada antes.

## Mediciones (19/10/2026, sin micrófono, voz sintética)

| Etapa | Tiempo |
|---|---|
| Voz a texto (Groq) | 0,35 a 1,1 s |
| Capa 1 con herramientas (gpt-oss-120b) | 0,4 a 0,8 s |
| Pedido completo desde el celular (/voz) | ~0,75 s |
| Voz Kokoro | 0,38 s por cada segundo de audio |
| Wake word en Kotlin vs Python | 0,9978 vs 0,998 (mismo audio) |
| Cuenta con `calcular` desde el celular | ~1,2 s |

## Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| El celular dice "No llego a la PC" | ¿Están en el mismo Wi-Fi? ¿`vloomy.cmd` abierto? ¿Permitiste el firewall? Probá desde el navegador del celular `http://192.168.1.4:8765/salud`: si dice "token inválido", la PC responde. Si la IP cambió, mirala en la ventana de `vloomy.cmd`. |
| "La PC respondió, pero el token no coincide" | Copiá de nuevo el token que muestra `vloomy.cmd`. |
| No reacciona a la palabra | Hablá claro, a menos de 1–2 m. En la PC revisá Configuración → Privacidad → Micrófono → apps de escritorio. Si sigue sin reaccionar, bajá el umbral en `voice\modelos\hey_vloomy.json`. |
| Se activa solo | Subí el `umbral` de `voice\modelos\hey_vloomy.json` (por ejemplo +0,1). En el celular hay que recompilar con `android\build.cmd`. |
| Corta antes de que termines | Subí `SILENCIO_FIN` en `voice\vloomy.py` y en `VloomyService.kt` (10 = 0,8 s). |
| Dice "[ia] … falló" | Groq sin cupo o sin internet: pasa solo a Ollama local, que la primera vez tarda en cargar. |
| "No pude: estabas usando el mouse…" | Windows-MCP cede el control mientras usás mouse o teclado. Soltalos y repetí (solo afecta atajos y ventanas). |
| La escucha del celular se cortó | Android a veces la mata para ahorrar batería. Abrí la app y tocá "Activar escucha". Después de reiniciar el celular también hay que activarla a mano (regla de Android 14+). |
| "La capa 2 no está abierta" | Abrí `capa2.cmd`. |
| En la PC no se oye a Vloomy | Vloomy habla por la salida predeterminada de Windows, que hoy es el **monitor LED (HDMI)**. Si no tiene parlantes, elegí tus parlantes o auriculares en Configuración → Sistema → Sonido → Salida. |
| La PC no te escucha bien | Usa el micrófono predeterminado (hoy el **micrófono USB**). Subí su nivel en Configuración → Sistema → Sonido → Entrada. |

## Protocolo PC ↔ celular

Todas las rutas piden el header `Authorization: Bearer <token>`. Puerto 8765.

| Ruta | Envío | Respuesta |
|---|---|---|
| `GET /salud` | — | `{"ok": true}` |
| `POST /voz` | WAV mono 16 kHz 16 bits con el pedido | NDJSON: `{"vos"}`, `{"decir"}`…, `{"preguntar","id"}`, `{"fin": true}` |
| `POST /responder/{id}` | WAV con la respuesta a "¿confirmo?" | `{"ok": true, "texto"}` |

## Comandos útiles

```powershell
cd D:\Claude\repos\vloomy\voice
.\.venv\Scripts\python.exe test_capa0.py       # comandos fijos (sin red)
.\.venv\Scripts\python.exe prueba.py           # punta a punta sin micrófono (usa Groq)
.\.venv\Scripts\python.exe entrenar_wake.py    # reentrenar "Hey Vloomy"
..\capa2\test_canal.py                         # con el mismo python: protocolo de la capa 2
D:\Claude\repos\vloomy\android\build.cmd       # tests del wake word + recompilar Vloomy.apk
```
