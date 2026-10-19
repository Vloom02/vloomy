"""Entrena el wake word "Hey Vloomy" con voces sintéticas de Kokoro sobre los features de openWakeWord.

Correr:  .venv\\Scripts\\python.exe entrenar_wake.py
Genera modelos\\hey_vloomy.onnx: entrada [N,16,96] y salida [N,1], el mismo formato que los modelos de
openWakeWord, así que lo usan igual la PC (vloomy.py) y el celular (android/wake).
Datos intermedios y negativos reales en ..\\.cache\\wake (ver PROGRESO.md para bajarlos).
"""
import json
import random
import time
from pathlib import Path

import numpy as np
import onnx
from kokoro_onnx import Kokoro
from onnx import TensorProto, helper, numpy_helper
from openwakeword.utils import AudioFeatures
from scipy.signal import fftconvolve, resample
from sklearn.neural_network import MLPClassifier

AQUI = Path(__file__).parent
CACHE = AQUI.parent / '.cache' / 'wake'
SALIDA = AQUI / 'modelos' / 'hey_vloomy.onnx'
KOKORO = AQUI.parent / '.cache' / 'kokoro'
SR, VENTANA = 16000, 32000  # 2 s: openWakeWord saca exactamente 16 embeddings de esto
FP_POR_HORA_MAX = 0.5       # objetivo de falsas activaciones con habla real

POSITIVOS = {'es-419': ['Hey Blumi', 'Ey Blumi', 'Hey Vloomy', 'Jey Blumi', 'Hey Blumi!'],
             'en-us': ['Hey Vloomy', 'Hey Bloomy', 'Hey Vloomie']}
NEGATIVOS = {
    'es-419': ['Hey', 'Hola', 'Bueno', 'Blusa', 'Lumi', 'Hey Jimmy', 'Hey Lumi', 'Hey Mimi', 'Ey vos', 'Dale',
               'Vamos', 'Pluma', 'Bloque', 'Hey Siri', 'Oye Lupe', 'Hey Google', 'Alexa', 'Hey Jarvis', 'Es mi blusa',
               'Le dije que sí', 'Pasame la sal', '¿Qué hora es?', 'Abrí el bloc de notas', 'Mañana llueve',
               'Hoy hace calor', 'Che, ¿cómo andás?', 'Tengo turno a las cinco', 'Blumberg', 'Umami', 'Tu mamá',
               'Fui al súper', 'No sé', 'Bien, ¿y vos?', 'Hey, mirá esto', 'Un mimo', 'Bolívar', 'Bulevar'],
    'en-us': ['Hey', 'Hello there', 'Blue moon', 'Hey Jimmy', 'Hey Lumi', 'Bloomberg', 'Hey Siri', 'Hey Google',
              'Hey Jarvis', 'Alexa', 'Gloomy day', 'Hey buddy', 'Loony', 'What time is it', 'Play some music',
              'Open the window', 'Good morning', 'Thank you very much', 'Plumber', 'Boomerang'],
}


def voces(tts):
    # Las voces de otros idiomas igual sirven: Kokoro aplica el timbre a la fonética del idioma pedido.
    return [v for v in tts.get_voices() if v[0] in 'abefip']


def sintetizar(tts, pedidos):
    clips = []
    for i, (texto, voz, lang, velocidad) in enumerate(pedidos):
        try:
            audio, sr = tts.create(texto, voice=voz, speed=velocidad, lang=lang)
        except Exception as e:
            print(f'   salteo {texto!r} {voz}: {e}')
            continue
        clips.append(resample(audio, int(len(audio) * SR / sr)).astype(np.float32))
        if i % 200 == 0:
            print(f'   {i}/{len(pedidos)}', flush=True)
    return clips


def aumentar(clip, rng, al_final):
    """Velocidad, volumen, eco y ruido; ubica la frase al final de la ventana si es positiva."""
    clip = resample(clip, int(len(clip) * rng.uniform(0.9, 1.1)))
    clip = clip / (np.abs(clip).max() + 1e-6) * rng.uniform(0.2, 0.9)
    if rng.random() < 0.5:
        largo = int(SR * rng.uniform(0.05, 0.4))
        ir = rng.normal(size=largo) * np.exp(-np.linspace(0, rng.uniform(4, 10), largo))
        ir[0] = 1
        clip = fftconvolve(clip, ir)[: len(clip)]
        clip = clip / (np.abs(clip).max() + 1e-6) * rng.uniform(0.2, 0.9)
    ventana = np.zeros(VENTANA, np.float32)
    fin = VENTANA - int(SR * rng.uniform(0.02, 0.25)) if al_final else int(rng.integers(min(len(clip), VENTANA), VENTANA + 1))
    clip = clip[-fin:]  # si es más largo que lo que entra, queda el final (lo que oye el detector)
    ventana[fin - len(clip):fin] = clip
    if rng.random() < 0.85:
        ruido = rng.normal(size=VENTANA)
        if rng.random() < 0.5:  # ruido "rosa": más grave, como una casa
            ruido = np.cumsum(ruido)
            ruido -= np.convolve(ruido, np.ones(400) / 400, mode='same')
        snr = rng.uniform(3, 30)
        p_voz = np.mean(ventana ** 2) + 1e-9
        ventana += ruido / (np.std(ruido) + 1e-9) * np.sqrt(p_voz / 10 ** (snr / 10))
    return (np.clip(ventana, -1, 1) * 32767).astype(np.int16)


def solo_ruido(rng, n):
    salida = []
    for _ in range(n):
        r = rng.normal(size=VENTANA) * rng.uniform(0.001, 0.2)
        if rng.random() < 0.5:
            r = np.cumsum(r) * 0.05
        salida.append((np.clip(r, -1, 1) * 32767).astype(np.int16))
    return salida


def features(af, clips):
    return af.embed_clips(np.stack(clips), batch_size=64).astype(np.float32)


def negativos_reales(rng, n):
    """Ventanas de habla y ruido reales ya procesadas por openWakeWord (ACAV100M, ~2000 h)."""
    for _ in range(120):  # si todavía se está bajando, numpy se queja del tamaño: espero
        try:
            acav = np.load(CACHE / 'acav100m_features.npy', mmap_mode='r')
            break
        except ValueError:
            time.sleep(30)
    print(f'   ACAV100M: {acav.shape} {acav.dtype}')
    elegidas = np.sort(rng.choice(acav.shape[0], size=min(n, acav.shape[0]), replace=False))
    return np.asarray(acav[elegidas], dtype=np.float32)


def exportar(clf, media, desvio, ruta):
    """MLP de sklearn -> ONNX con la normalización metida en la primera capa."""
    pesos = [w.astype(np.float32) for w in clf.coefs_]
    sesgos = [b.astype(np.float32) for b in clf.intercepts_]
    sesgos[0] = (sesgos[0] - (media / desvio) @ pesos[0]).astype(np.float32)
    pesos[0] = (pesos[0] / desvio[:, None]).astype(np.float32)
    nodos, inits = [helper.make_node('Reshape', ['x', 'forma'], ['h0'])], [numpy_helper.from_array(np.array([-1, 16 * 96], np.int64), 'forma')]
    for i, (w, b) in enumerate(zip(pesos, sesgos)):
        inits += [numpy_helper.from_array(w, f'w{i}'), numpy_helper.from_array(b, f'b{i}')]
        nodos.append(helper.make_node('Gemm', [f'h{i}', f'w{i}', f'b{i}'], [f'g{i}']))
        ultima = i == len(pesos) - 1
        nodos.append(helper.make_node('Sigmoid' if ultima else 'Relu', [f'g{i}'], ['y' if ultima else f'h{i + 1}']))
    grafo = helper.make_graph(nodos, 'hey_vloomy',
                              [helper.make_tensor_value_info('x', TensorProto.FLOAT, ['N', 16, 96])],
                              [helper.make_tensor_value_info('y', TensorProto.FLOAT, ['N', 1])], inits)
    modelo = helper.make_model(grafo, opset_imports=[helper.make_opsetid('', 13)])
    modelo.ir_version = 8  # que lo abra también onnxruntime 1.20 de Android
    onnx.checker.check_model(modelo)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(modelo, ruta)


def main():
    t0 = time.time()
    rng = np.random.default_rng(7)
    random.seed(7)
    CACHE.mkdir(parents=True, exist_ok=True)
    tts = Kokoro(str(KOKORO / 'kokoro-v1.0.onnx'), str(KOKORO / 'voices-v1.0.bin'))
    todas = voces(tts)
    prueba = set(random.sample(todas, 6))  # voces que el modelo nunca escucha al entrenar
    print(f'{len(todas)} voces; de prueba: {sorted(prueba)}')

    cache_clips = CACHE / 'clips.npz'
    if cache_clips.exists():
        datos = np.load(cache_clips, allow_pickle=True)
        pos, neg, voz_pos = list(datos['pos']), list(datos['neg']), list(datos['voz_pos'])
    else:
        print('1) sintetizando positivos…')
        pedidos = [(t, v, lang, s) for v in todas for lang, textos in POSITIVOS.items() for t in textos
                   for s in (0.85, 1.0, 1.15, 1.3)]
        pos = sintetizar(tts, pedidos)
        voz_pos = [p[1] for p in pedidos][: len(pos)]
        print('2) sintetizando negativos…')
        pedidos = [(t, v, lang, float(rng.uniform(0.85, 1.3))) for v in todas for lang, textos in NEGATIVOS.items()
                   for t in random.sample(textos, 8)]
        neg = sintetizar(tts, pedidos)
        np.savez(cache_clips, pos=np.array(pos, dtype=object), neg=np.array(neg, dtype=object),
                 voz_pos=np.array(voz_pos))

    af = AudioFeatures()
    print(f'3) aumentando y sacando features… ({time.time() - t0:.0f} s)')
    es_prueba = np.array([v in prueba for v in voz_pos])
    entren = [c for c, p in zip(pos, es_prueba) if not p]
    x_pos = features(af, [aumentar(c, rng, True) for c in entren for _ in range(4)])
    x_pos_prueba = features(af, [aumentar(c, rng, True) for c, p in zip(pos, es_prueba) if p])
    x_neg = features(af, [aumentar(c, rng, False) for c in neg for _ in range(2)] + solo_ruido(rng, 1000))
    x_real = negativos_reales(rng, 200_000)
    print(f'   positivos {len(x_pos)} (+{len(x_pos_prueba)} de prueba), negativos sintéticos {len(x_neg)}, '
          f'reales {len(x_real)}')

    x = np.concatenate([x_pos, x_neg, x_real]).reshape(-1, 16 * 96)
    y = np.concatenate([np.ones(len(x_pos)), np.zeros(len(x_neg) + len(x_real))])
    # Los positivos son pocos: los repito para que el modelo no aprenda a decir siempre "no".
    repetir = max(1, int(len(x_real) / len(x_pos) / 4))
    x = np.concatenate([x, np.repeat(x[: len(x_pos)], repetir - 1, axis=0)])
    y = np.concatenate([y, np.ones(len(x_pos) * (repetir - 1))])
    media, desvio = x.mean(axis=0), x.std(axis=0) + 1e-6

    print(f'4) entrenando con {len(x)} ejemplos… ({time.time() - t0:.0f} s)')
    clf = MLPClassifier(hidden_layer_sizes=(128, 64), alpha=1e-3, batch_size=512, max_iter=30,
                        early_stopping=True, validation_fraction=0.1, n_iter_no_change=4, random_state=7, verbose=True)
    clf.fit((x - media) / desvio, y)

    print(f'5) evaluando… ({time.time() - t0:.0f} s)')
    # Habla y ruido reales continuos (~11 h, un frame cada 80 ms): ventanas de 16 frames, como en vivo.
    frames = np.load(CACHE / 'validation_set_features.npy').astype(np.float32)
    ventanas = np.lib.stride_tricks.sliding_window_view(frames, (16, 96))[:, 0].reshape(-1, 16 * 96)
    p_val = np.concatenate([clf.predict_proba((ventanas[i:i + 50_000] - media) / desvio)[:, 1]
                            for i in range(0, len(ventanas), 50_000)])
    p_pos = clf.predict_proba((x_pos_prueba.reshape(-1, 16 * 96) - media) / desvio)[:, 1]
    horas = len(frames) * 0.08 / 3600
    tabla = []
    for umbral in np.arange(0.3, 0.99, 0.05):
        arriba = p_val >= umbral
        fp = (arriba[0] + np.sum(arriba[1:] & ~arriba[:-1])) / horas  # activaciones, no ventanas sueltas
        tabla.append((float(umbral), float((p_pos >= umbral).mean()), float(fp)))
        print(f'   umbral {umbral:.2f}: detecta {tabla[-1][1]:.0%} con voces nuevas | {fp:.2f} falsas/hora')
    validos = [t for t in tabla if t[2] <= FP_POR_HORA_MAX] or [tabla[-1]]
    umbral, recall, fp = max(validos, key=lambda t: (t[1], t[0]))
    print(f'   elegido: umbral {umbral:.2f} -> detecta {recall:.0%}, {fp:.2f} falsas/hora '
          f'(validación: {horas:.1f} h de audio real)')

    exportar(clf, media, desvio, SALIDA)
    SALIDA.with_suffix('.json').write_text(json.dumps(
        {'umbral': round(umbral, 2), 'detecta_voces_nuevas': round(recall, 3), 'falsas_por_hora': round(fp, 3),
         'horas_validacion': round(horas, 1)}, indent=2))
    import onnxruntime as ort
    s = ort.InferenceSession(str(SALIDA))
    muestra = x_pos_prueba[:8]
    diferencia = np.abs(s.run(None, {'x': muestra})[0][:, 0] - clf.predict_proba((muestra.reshape(-1, 1536) - media) / desvio)[:, 1]).max()
    assert diferencia < 1e-4, f'el ONNX no coincide con sklearn ({diferencia})'
    print(f'listo: {SALIDA} ({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
