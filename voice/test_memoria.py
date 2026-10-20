"""Correr con:  .venv\\Scripts\\python.exe test_memoria.py   (sin red)"""
import datetime
import tempfile

from memoria import Memoria, coincide, cuando_desde, cuando_texto

ahora = datetime.datetime(2026, 10, 20, 19, 0)  # martes

# Cuándo
assert cuando_desde(ahora, minutos=20) == datetime.datetime(2026, 10, 20, 19, 20)
assert cuando_desde(ahora, fecha_hora='07:00') == datetime.datetime(2026, 10, 21, 7, 0)  # ya pasó: mañana
assert cuando_desde(ahora, fecha_hora='21:30') == datetime.datetime(2026, 10, 20, 21, 30)
assert cuando_desde(ahora, fecha_hora='2026-10-26T10:00') == datetime.datetime(2026, 10, 26, 10, 0)
for malo in [dict(minutos=0), dict(fecha_hora='2026-10-19T10:00'), dict(), dict(fecha_hora='mañana')]:
    try:
        cuando_desde(ahora, **malo)
        raise AssertionError(f'tenía que fallar: {malo}')
    except ValueError:
        pass

assert cuando_texto(datetime.datetime(2026, 10, 20, 19, 30), ahora) == 'hoy a las 19:30'
assert cuando_texto(datetime.datetime(2026, 10, 21, 7, 0), ahora) == 'mañana a las 07:00'
assert cuando_texto(datetime.datetime(2026, 10, 26, 10, 0), ahora) == 'el lunes 26 de octubre a las 10:00'

assert coincide('lo del dentista', 'El turno del dentista es el martes')
assert not coincide('la ropa', 'El turno del dentista es el martes')
assert not coincide('de', 'El turno del dentista')  # nada de borrar por una palabra vacía

with tempfile.TemporaryDirectory() as carpeta:
    m = Memoria(carpeta)
    # Datos
    assert m.recordar('Vivo en Rosario', ahora.date()) == 'Listo, me lo acuerdo.'
    assert m.recordar('vivo en rosario', ahora.date()) == 'Eso ya lo tenía anotado.'
    m.recordar('Mi dentista es el martes a las 10', ahora.date())
    assert [d['texto'] for d in Memoria(carpeta).datos()] == ['Vivo en Rosario', 'Mi dentista es el martes a las 10']
    assert m.olvidar('lo del dentista').startswith('Listo')
    assert m.olvidar('lo del dentista') == 'No tenía nada anotado sobre eso.'
    # Recordatorios: persisten, se ordenan y salen cuando tocan
    m.agregar_recordatorio('sacar la ropa', ahora + datetime.timedelta(minutes=20))
    m.agregar_recordatorio('despertarme', datetime.datetime(2026, 10, 21, 7, 0), alarma=True)
    m.agregar_recordatorio('llamar a mamá', ahora + datetime.timedelta(minutes=5))
    assert [r['texto'] for r in Memoria(carpeta).recordatorios()] == ['llamar a mamá', 'sacar la ropa', 'despertarme']
    assert m.vencidos(ahora) == []
    tocan = m.vencidos(ahora + datetime.timedelta(minutes=21))
    assert [r['texto'] for r in tocan] == ['llamar a mamá', 'sacar la ropa']
    assert [r['texto'] for r in m.recordatorios()] == ['despertarme'] and m.recordatorios()[0]['alarma']
    assert m.borrar_recordatorios('la ropa') == 0
    assert m.borrar_recordatorios('todos') == 1 and m.recordatorios() == []
    # Ajustes
    assert m.ajuste('voz', 'argentina') == 'argentina'
    m.guardar_ajuste('voz', 'latina')
    assert Memoria(carpeta).ajuste('voz', 'argentina') == 'latina'

print('ok: memoria y recordatorios')
