"""Prueba de punta a punta sin micrófono: Kokoro genera la voz que "escucha" Vloomy.

Correr:  .venv\\Scripts\\python.exe prueba.py
Usa cupo gratis de Groq (unos 10 pedidos). Las herramientas se simulan salvo en el servidor,
donde solo se hace una pregunta que no necesita herramientas: no toca tu PC.
"""
import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

os.environ['VLOOMY_HOST'] = '127.0.0.1'  # la prueba no abre el puerto a la red
os.environ['VLOOMY_PUERTO'] = '8799'

import numpy as np
from kokoro_onnx import Kokoro
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openwakeword.model import Model
from scipy.signal import resample_poly

import capa0
import vloomy as V


def voz_16k(tts, texto, voz='em_alex', lang='es-419'):
    audio, _ = tts.create(texto, voice=voz, speed=1.0, lang=lang)
    pcm = resample_poly(audio, 2, 3)  # 24 kHz -> 16 kHz
    return (np.clip(pcm, -1, 1) * 32767).astype(np.int16)


def seguidos_wake(clip):
    """Por modelo: máximo de bloques seguidos arriba de su umbral (Vloomy se activa con WAKE_PACIENCIA)."""
    oww = Model(wakeword_model_paths=list(V.WAKE_MODELOS))
    umbrales = {Path(r).stem: u for r, u in V.WAKE_MODELOS.items()}
    clip = np.concatenate([np.zeros(16000, np.int16), clip, np.zeros(16000, np.int16)])
    actual, maximo = dict.fromkeys(umbrales, 0), dict.fromkeys(umbrales, 0)
    for i in range(0, len(clip) - 1279, 1280):
        for nombre, p in oww.predict(clip[i:i + 1280]).items():
            actual[nombre] = actual[nombre] + 1 if p >= umbrales[nombre] else 0
            maximo[nombre] = max(maximo[nombre], actual[nombre])
    return maximo


def post(ruta, cuerpo, token):
    req = urllib.request.Request(f'http://127.0.0.1:8799{ruta}', data=cuerpo, method='POST' if cuerpo else 'GET',
                                 headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, [json.loads(linea) for linea in r]
    except urllib.error.HTTPError as e:
        return e.code, []


async def main():
    for fin in ['Gracias.', '¡Muchas gracias!', 'Listo', 'Chau', 'Bueno, gracias', 'Nada más.']:
        assert V.FIN_CHARLA.match(capa0.normalizar(fin)), fin
    for pedido in ['Gracias, ahora abrí Spotify', '¿Qué hora es?', 'Listo, poné música']:
        assert not V.FIN_CHARLA.match(capa0.normalizar(pedido)), pedido

    # Capa 2: cómo se resume lo que devuelve `claude -p --output-format json`.
    ok = json.dumps({'is_error': False, 'result': 'Los mejores son X e Y.',
                     'permission_denials': [{'tool_name': 'Bash'}]})
    assert V.resumen_claude(ok, '') == 'Claude terminó: Los mejores son X e Y. No lo dejé usar: Bash.'
    assert 'iniciá sesión' in V.resumen_claude(json.dumps({'is_error': True, 'result': 'Not logged in · Please run /login'}), '')
    assert 'confiar' in V.resumen_claude('', 'this workspace has not been trusted')

    v = V.Vloomy()
    tts = Kokoro(str(V.KOKORO / 'kokoro-v1.0.onnx'), str(V.KOKORO / 'voices-v1.0.bin'))

    jarvis = seguidos_wake(voz_16k(tts, 'Hey Jarvis!', 'am_michael', 'en-us'))
    comun = seguidos_wake(voz_16k(tts, 'Hola, ¿cómo andás? Hoy hace calor.'))
    print(f'wake word (bloques seguidos arriba del umbral): "Hey Jarvis" {jarvis} | frase común {comun}')
    assert jarvis['hey_jarvis_v0.1'] >= V.WAKE_PACIENCIA
    assert all(n < V.WAKE_PACIENCIA for n in comun.values())
    if V.VLOOMY_MODEL.exists():  # af_heart quedó afuera del entrenamiento: es una voz nueva para el modelo
        vloomy = seguidos_wake(voz_16k(tts, 'Hey Blumi!', 'af_heart', 'es-419'))
        print(f'wake word: "Hey Blumi" con voz nueva {vloomy}')
        assert vloomy['hey_vloomy'] >= V.WAKE_PACIENCIA

    for frase, esperado in [('Abrí el bloc de notas.', ('abrir', 'bloc de notas')), ('¿Qué hora es?', ('hora', None))]:
        t = time.perf_counter()
        texto = await v.transcribir(voz_16k(tts, frase))
        print(f'voz a texto: {texto!r} en {(time.perf_counter() - t) * 1000:.0f} ms -> capa 0 {capa0.parse(texto)}')
        assert capa0.parse(texto) == esperado

    apps = await asyncio.to_thread(capa0.apps_instaladas)
    print(f'menú Inicio: {len(apps)} apps; "bloc de notas" -> {capa0.buscar_app("bloc de notas", apps)!r}, '
          f'"calculadora" -> {capa0.buscar_app("calculadora", apps)!r}')

    params = StdioServerParameters(command=str(V.WINDOWS_MCP), args=['serve', '--tools', ','.join(V.MCP_PERMITIDAS)],
                                   env={**os.environ})
    async with stdio_client(params, errlog=open(os.devnull, 'w')) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        v.herramientas += [{'type': 'function', 'function': {'name': t.name, 'description': t.description,
                                                              'parameters': t.input_schema}}
                           for t in (await s.list_tools()).tools if t.name in V.MCP_PERMITIDAS]

    usadas = []
    ejecutar_real = v.ejecutar

    async def simular(nombre, args, confirmar):
        usadas.append((nombre, args))
        return capa0.calcular(args['expresion']) if nombre == 'calcular' else 'Hecho.'  # calcular no toca la PC

    v.ejecutar = simular
    cliente, modelo, extra = next(v.proveedores())
    for pedido in ['¿Cuánto es quince por siete?', 'Poné la música un poco más fuerte', 'Abrí la calculadora']:
        usadas.clear()
        msgs = [{'role': 'system', 'content': V.SISTEMA.format(ahora='lunes 19 de octubre 10:00')},
                {'role': 'user', 'content': pedido}]
        t = time.perf_counter()
        respuesta = await v.conversar(cliente, modelo, extra, msgs, lambda frase: None, None)
        print(f'{modelo} | {pedido} -> {respuesta!r} {usadas} | {(time.perf_counter() - t) * 1000:.0f} ms')
        if 'quince' in pedido:
            assert '105' in respuesta or 'ciento cinco' in respuesta.lower(), respuesta

    # Servidor del celular: HTTP real, token y respuesta en streaming.
    v.ejecutar = ejecutar_real
    v.herramientas = list(V.LOCALES)
    servidor = asyncio.create_task(v.correr(con_pc=False))
    await asyncio.sleep(4)
    token = V.token_celular()
    wav = V.a_wav(voz_16k(tts, '¿Cuánto es quince por siete?'))
    assert (await asyncio.to_thread(post, '/salud', None, 'token-falso'))[0] == 401
    assert (await asyncio.to_thread(post, '/salud', None, token))[0] == 200
    assert (await asyncio.to_thread(post, '/voz', wav, 'token-falso'))[0] == 401
    t = time.perf_counter()
    estado, eventos = await asyncio.to_thread(post, '/voz', wav, token)
    print(f'servidor /voz -> {estado} {eventos} | {(time.perf_counter() - t) * 1000:.0f} ms')
    assert estado == 200 and eventos[0].get('vos') and eventos[-1] == {'fin': True, 'seguir': True}
    assert any('105' in e.get('decir', '') or 'ciento cinco' in e.get('decir', '').lower() for e in eventos)
    servidor.cancel()

    # Arranque real como programa (con vloomy.log), como lo hace vloomy.cmd: tiene que levantar el servidor.
    import subprocess, sys
    env = {**os.environ, 'VLOOMY_HOST': '127.0.0.1', 'VLOOMY_PUERTO': '8798', 'PYTHONIOENCODING': 'utf-8'}
    proc = subprocess.Popen([sys.executable, 'vloomy.py', '--sin-pc'], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        vivo = False
        for _ in range(60):
            await asyncio.sleep(0.5)
            req = urllib.request.Request('http://127.0.0.1:8798/salud')
            try:
                urllib.request.urlopen(req, timeout=2)
            except urllib.error.HTTPError as e:
                vivo = e.code == 401
            except OSError:
                pass
            if vivo or proc.poll() is not None:
                break
        assert vivo, f'vloomy.py no arrancó (código {proc.poll()}); mirá vloomy.log'
        print('arranque real de vloomy.py: ok')
    finally:
        proc.kill()
    print('ok')

asyncio.run(main())
