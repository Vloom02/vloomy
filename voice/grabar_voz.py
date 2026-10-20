"""Grabación guiada para ajustar "Hey Vloomy" a tu voz (después correr entrenar_wake.py).

Correr:  grabar_voz.cmd (en la raíz del proyecto). Unos 2 minutos.
Guarda en ..\\.cache\\wake\\usuario\\: pos_XX.wav (la palabra) y neg_XX.wav (hablando normal).
"""
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

import vloomy as V

CARPETA = V.ROOT / '.cache' / 'wake' / 'usuario'
VECES, SEG_PALABRA, SEG_CHARLA = 20, 2.5, 10
CONSEJOS = ['normal', 'normal', 'más bajo', 'más rápido', 'más lento', 'como si estuvieras lejos', 'normal',
            'con ganas', 'cansado', 'normal']


def guardar(nombre, audio):
    with wave.open(str(CARPETA / nombre), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(V.SR)
        w.writeframes(audio.tobytes())


def grabar(segundos):
    audio = sd.rec(int(segundos * V.SR), samplerate=V.SR, channels=1, dtype='int16')
    sd.wait()
    return audio[:, 0]


def detectado(audio):
    """¿Lo detecta el modelo actual, con la misma paciencia que Vloomy?"""
    oww = Model(wakeword_model_paths=list(V.WAKE_MODELOS))
    umbral = V.WAKE_MODELOS[str(V.VLOOMY_MODEL)]
    audio = np.concatenate([audio, np.zeros(V.SR, np.int16)])
    seguidos = maximo = 0
    for i in range(0, len(audio) - V.CHUNK + 1, V.CHUNK):
        p = oww.predict(audio[i:i + V.CHUNK])['hey_vloomy']
        seguidos = seguidos + 1 if p >= umbral else 0
        maximo = max(maximo, p)
        if seguidos >= V.WAKE_PACIENCIA:
            return True, maximo
    return False, maximo


CARPETA.mkdir(parents=True, exist_ok=True)
print(f"Micrófono: {sd.query_devices(kind='input')['name']}\n")
print(f'1) Vas a decir "Hey Vloomy" {VECES} veces. Cuando aparezca  >>> AHORA  decilo UNA vez.')
input('   Apretá Enter para empezar…')
aciertos = 0
for i in range(VECES):
    print(f'\n   [{i + 1}/{VECES}] decilo {CONSEJOS[i % len(CONSEJOS)]}… ', end='', flush=True)
    time.sleep(0.8)
    print('>>> AHORA', flush=True)
    audio = grabar(SEG_PALABRA)
    guardar(f'pos_{i:02d}.wav', audio)
    ok, maximo = detectado(audio)
    aciertos += ok
    nivel = int(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    print(f"   {'detectado' if ok else 'NO detectado'} (puntaje máx {maximo:.2f}, volumen {nivel})")
print(f'\n   El modelo actual te detectó {aciertos} de {VECES}.')

print(f'\n2) Ahora hablá normal {3 * SEG_CHARLA} segundos SIN decir la palabra (contá qué hiciste hoy, leé algo…).')
input('   Apretá Enter y empezá a hablar…')
for i in range(3):
    print(f'   grabando {i + 1}/3…', flush=True)
    guardar(f'neg_{i:02d}.wav', grabar(SEG_CHARLA))
print(f'\nListo. Grabaciones en {CARPETA}')
