"""Correr con:  .venv\\Scripts\\python.exe test_capa0.py"""
import datetime

from capa0 import buscar_app, calcular, ejecutar_local, parse

CASOS = {
    'Hey Jarvis, abrí Spotify': ('abrir', 'spotify'),
    'abrí el bloc de notas': ('abrir', 'bloc de notas'),
    'Vloomy abrime Google Chrome por favor': ('abrir', 'google chrome'),
    'Subí el volumen': ('volumen_arriba', None),
    'bajale el volumen un poco': ('volumen_abajo', None),
    'silencio': ('silencio', None),
    'Pausá la música.': ('play_pausa', None),
    'siguiente canción': ('siguiente', None),
    '¿Qué hora es?': ('hora', None),
    '¿Qué día es hoy?': ('fecha', None),
    'bloqueá la compu': ('bloquear', None),
    # Esto lo tiene que pensar la IA, no la capa 0:
    'abrí el bloc de notas y escribí hola': None,
    'abrí la carpeta de descargas del proyecto de la peluquería': None,
    '¿cuánto es 15 por 7?': None,
    'contame un chiste': None,
}

for texto, esperado in CASOS.items():
    obtenido = parse(texto)
    assert obtenido == esperado, f'{texto!r}: esperaba {esperado}, obtuve {obtenido}'

ahora = datetime.datetime(2026, 10, 19, 9, 5)
assert ejecutar_local('hora', ahora) == 'Son las 09:05.'
assert ejecutar_local('fecha', ahora) == 'Hoy es lunes 19 de octubre.'

APPS = {'Bloc de notas': 1, 'Calculadora': 2, 'Google Chrome': 3, 'Chrome Remote Desktop': 4, 'Spotify': 5}
assert buscar_app('bloc de notas', APPS) == 'Bloc de notas'
assert buscar_app('la calculadora', APPS) == 'Calculadora'
assert buscar_app('chrome', APPS) == 'Google Chrome'
assert buscar_app('espotifai', APPS) == 'Spotify'  # como lo transcribe Whisper si lo decís en castellano
assert buscar_app('spotfy', APPS) == 'Spotify'
assert buscar_app('photoshop', APPS) is None

assert calcular('15*7') == '105'
assert calcular('3.5 * 60') == '210'
assert calcular('23 x 4') == '92'
assert calcular('(1 + 2) ** 3 - 10 / 4') == '24.5'
assert calcular('1,5 + 1') == '2.5'
assert calcular('-8 // 3') == '-3'
assert calcular('__import__("os").system("dir")').startswith('No pude')
assert calcular('2 ** 100000').startswith('No pude')
assert calcular('1/0').startswith('No pude')

print(f'ok: {len(CASOS) + 17} casos')
