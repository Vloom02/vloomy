"""Diagnóstico del micrófono: muestra en vivo el volumen y el puntaje de cada palabra de activación.

Correr:  diagnostico.cmd (en la raíz del proyecto). Dura 60 s, o los segundos que le pases.
"""
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

import vloomy as V

segundos = int(sys.argv[1]) if len(sys.argv) > 1 else 60
print(f"Micrófono: {sd.query_devices(kind='input')['name']}")
print(f"Parlantes: {sd.query_devices(kind='output')['name']}")
print('Hablá normal y decí "Hey Vloomy" o "Hey Jarvis". La barra tiene que moverse cuando hablás.\n')
oww = Model(wakeword_model_paths=list(V.WAKE_MODELOS))
umbrales = {Path(r).stem: u for r, u in V.WAKE_MODELOS.items()}
seguidos = dict.fromkeys(umbrales, 0)
maximo = 0
with sd.InputStream(samplerate=V.SR, channels=1, dtype='int16', blocksize=V.CHUNK) as entrada:
    for _ in range(segundos * V.SR // V.CHUNK):
        x = entrada.read(V.CHUNK)[0][:, 0]
        nivel = int(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
        maximo = max(maximo, nivel)
        puntajes = oww.predict(x)
        detalle = '  '.join(f"{n.split('_v0')[0]} {p:.2f}" for n, p in puntajes.items())
        print(f"\rvolumen {nivel:5d} {'#' * min(30, nivel // 100):<30} {detalle}   ", end='', flush=True)
        for n, p in puntajes.items():
            seguidos[n] = seguidos[n] + 1 if p >= umbrales[n] else 0
            if seguidos[n] == V.WAKE_PACIENCIA:
                print(f'\n>>> DETECTADO: {n}')
print(f'\n\nVolumen máximo: {maximo} (hablando normal debería pasar de 500; si no pasa de 100, el micrófono llega casi mudo)')
