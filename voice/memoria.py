"""Lo que Vloomy guarda entre reinicios: datos que le pediste recordar y recordatorios.

Vive en ../datos (fuera de git). Todo es puro salvo la lectura y escritura de los JSON; se prueba en test_memoria.py.
"""
import datetime
import json
import os
from pathlib import Path

import capa0


def cuando_desde(ahora, minutos=None, fecha_hora=None):
    """Momento de un recordatorio: dentro de `minutos`, o a una fecha y hora ISO ("2026-10-21T07:00")
    o solo una hora ("07:00": hoy, o mañana si ya pasó)."""
    if minutos is not None:
        if float(minutos) <= 0:
            raise ValueError('los minutos tienen que ser más que cero')
        return ahora + datetime.timedelta(minutes=float(minutos))
    if not fecha_hora:
        raise ValueError('falta cuándo')
    texto = str(fecha_hora).strip()
    if 'T' in texto or '-' in texto:
        cuando = datetime.datetime.fromisoformat(texto)
    else:
        hora = datetime.time.fromisoformat(texto)
        cuando = datetime.datetime.combine(ahora.date(), hora)
        if cuando <= ahora:
            cuando += datetime.timedelta(days=1)
    if cuando <= ahora:
        raise ValueError('esa hora ya pasó')
    return cuando.replace(second=0, microsecond=0)


def cuando_texto(cuando, ahora):
    """Cómo decir el momento: "hoy a las 19:30", "mañana a las 07:00", "el lunes 26 de octubre a las 10:00"."""
    dias = (cuando.date() - ahora.date()).days
    hora = f'a las {cuando:%H:%M}'
    if dias == 0:
        return f'hoy {hora}'
    if dias == 1:
        return f'mañana {hora}'
    return f'el {capa0._DIAS[cuando.weekday()]} {cuando.day} de {capa0._MESES[cuando.month - 1]} {hora}'


def coincide(pedido, texto):
    """¿El pedido ("lo del dentista") se refiere a este texto? Todas sus palabras importantes tienen que estar."""
    palabras = [p for p in capa0.normalizar(pedido).split() if len(p) > 3]
    destino = capa0.normalizar(texto)
    return bool(palabras) and all(p in destino for p in palabras)


class Memoria:
    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def _leer(self, nombre):
        try:
            return json.loads((self.carpeta / nombre).read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _guardar(self, nombre, datos):
        tmp = self.carpeta / f'{nombre}.tmp'
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(tmp, self.carpeta / nombre)  # si se corta la luz a mitad, el archivo viejo queda entero

    # ---------- ajustes (por ejemplo, qué voz usar) ----------

    def ajuste(self, nombre, defecto=None):
        ajustes = self._leer('ajustes.json')
        return ajustes.get(nombre, defecto) if isinstance(ajustes, dict) else defecto

    def guardar_ajuste(self, nombre, valor):
        ajustes = self._leer('ajustes.json')
        self._guardar('ajustes.json', {**(ajustes if isinstance(ajustes, dict) else {}), nombre: valor})

    # ---------- datos que el usuario pidió recordar ----------

    def datos(self):
        return self._leer('memoria.json')

    def recordar(self, texto, hoy):
        datos = self.datos()
        if any(capa0.normalizar(d['texto']) == capa0.normalizar(texto) for d in datos):
            return 'Eso ya lo tenía anotado.'
        datos.append({'texto': texto.strip(), 'fecha': hoy.isoformat()})
        self._guardar('memoria.json', datos[-100:])
        return 'Listo, me lo acuerdo.'

    def olvidar(self, pedido):
        datos = self.datos()
        quedan = [d for d in datos if not coincide(pedido, d['texto'])]
        if len(quedan) == len(datos):
            return 'No tenía nada anotado sobre eso.'
        self._guardar('memoria.json', quedan)
        return f'Listo, me olvidé {len(datos) - len(quedan)} cosa{"s" if len(datos) - len(quedan) > 1 else ""}.'

    # ---------- recordatorios y alarmas ----------

    def recordatorios(self):
        return sorted(self._leer('recordatorios.json'), key=lambda r: r['cuando'])

    def agregar_recordatorio(self, texto, cuando, alarma=False):
        lista = self.recordatorios()
        nuevo = {'id': max((r['id'] for r in lista), default=0) + 1, 'texto': texto.strip(),
                 'cuando': cuando.isoformat(timespec='seconds'), 'alarma': bool(alarma)}
        self._guardar('recordatorios.json', lista + [nuevo])
        return nuevo

    def borrar_recordatorios(self, pedido):
        lista = self.recordatorios()
        todos = capa0.normalizar(pedido) in ('todos', 'todo', 'todas')
        quedan = [] if todos else [r for r in lista if not coincide(pedido, r['texto'])]
        self._guardar('recordatorios.json', quedan)
        return len(lista) - len(quedan)

    def vencidos(self, ahora):
        """Saca y devuelve los recordatorios que ya tocan."""
        lista = self.recordatorios()
        tocan = [r for r in lista if datetime.datetime.fromisoformat(r['cuando']) <= ahora]
        if tocan:
            self._guardar('recordatorios.json', [r for r in lista if r not in tocan])
        return tocan
