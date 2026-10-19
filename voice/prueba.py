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


def puntaje_wake(clip):
    oww = Model(wakeword_model_paths=[V.WAKE_MODEL])
    clip = np.concatenate([np.zeros(16000, np.int16), clip, np.zeros(16000, np.int16)])
    return max(list(oww.predict(clip[i:i + 1280]).values())[0] for i in range(0, len(clip) - 1279, 1280))


def post(ruta, cuerpo, token):
    req = urllib.request.Request(f'http://127.0.0.1:8799{ruta}', data=cuerpo, method='POST' if cuerpo else 'GET',
                                 headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, [json.loads(linea) for linea in r]
    except urllib.error.HTTPError as e:
        return e.code, []


async def main():
    v = V.Vloomy()
    tts = Kokoro(str(V.KOKORO / 'kokoro-v1.0.onnx'), str(V.KOKORO / 'voices-v1.0.bin'))

    si = puntaje_wake(voz_16k(tts, 'Hey Jarvis!', 'am_michael', 'en-us'))
    no = puntaje_wake(voz_16k(tts, 'Hola, ¿cómo andás? Hoy hace calor.'))
    print(f'wake word: "Hey Jarvis" {si:.2f} | frase común {no:.2f} (umbral {V.WAKE_UMBRAL})')
    assert si >= V.WAKE_UMBRAL > no

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
        return 'Hecho.'

    v.ejecutar = simular
    cliente, modelo, extra = next(v.proveedores())
    for pedido in ['¿Cuánto es quince por siete?', 'Poné la música un poco más fuerte', 'Abrí la calculadora']:
        usadas.clear()
        msgs = [{'role': 'system', 'content': V.SISTEMA.format(ahora='lunes 19 de octubre 10:00')},
                {'role': 'user', 'content': pedido}]
        t = time.perf_counter()
        respuesta = await v.conversar(cliente, modelo, extra, msgs, lambda frase: None, None)
        print(f'{modelo} | {pedido} -> {respuesta!r} {usadas} | {(time.perf_counter() - t) * 1000:.0f} ms')

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
    assert estado == 200 and eventos[0].get('vos') and eventos[-1] == {'fin': True}
    assert any('105' in e.get('decir', '') or 'ciento cinco' in e.get('decir', '').lower() for e in eventos)
    servidor.cancel()
    print('ok')

asyncio.run(main())
