"""Capa 0: comandos fijos que se resuelven sin IA, en milisegundos.

parse() es pura (se testea en test_capa0.py); ejecutar_local() toca Windows.
"""
import ast
import ctypes
import datetime
import difflib
import json
import operator
import re
import subprocess
import unicodedata

# Teclas virtuales de Windows para multimedia.
VK = {
    'volumen_arriba': 0xAF,
    'volumen_abajo': 0xAE,
    'silencio': 0xAD,
    'play_pausa': 0xB3,
    'siguiente': 0xB0,
    'anterior': 0xB1,
}
ACCIONES_LOCALES = [*VK, 'bloquear', 'hora', 'fecha']

_PREFIJO = re.compile(r'^(?:(?:hey|ey|oye|che)\s+)?(?:jarvis|vloomy|blumi|bloomy)\b[\s,]*')
_REGLAS = [
    (r'\b(?:subi|sube|subir|subime|subile|mas)\b.*\bvolumen\b|\bvolumen\b.*\b(?:arriba|mas alto)\b', 'volumen_arriba'),
    (r'\b(?:baja|bajale|bajar|bajame|menos)\b.*\bvolumen\b|\bvolumen\b.*\b(?:abajo|mas bajo)\b', 'volumen_abajo'),
    (r'^(?:silencio|silencia(?:lo)?|mutea(?:lo)?|mute)\b', 'silencio'),
    (r'^(?:pausa|pausala|pone pausa|play|pone play|reproduci|reanuda|segui con la musica)\b(?: (?:la )?(?:musica|cancion|tema))?$', 'play_pausa'),
    (r'^(?:siguiente|proxima|pasala|pasa de tema|siguiente (?:cancion|tema))$', 'siguiente'),
    (r'^(?:anterior|volve(?: al tema)? anterior|(?:cancion|tema) anterior)$', 'anterior'),
    (r'^(?:bloquea|bloquear)(?: la)? (?:pc|compu|computadora)$', 'bloquear'),
    (r'^(?:que hora es|decime la hora|la hora|hora)$', 'hora'),
    (r'^(?:que (?:dia|fecha) es(?: hoy)?|que dia es hoy)$', 'fecha'),
]
_ABRIR = re.compile(r'^(?:abri|abre|abrir|abrime|ejecuta|inicia|lanza)\s+(?:el |la |los |las )?(?P<app>.+)$')

_DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
          'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def normalizar(texto):
    sin_tildes = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    limpio = re.sub(r'[^a-z0-9+ ]', ' ', sin_tildes.lower())
    limpio = re.sub(r'\s+', ' ', limpio).strip()
    limpio = _PREFIJO.sub('', limpio)
    return re.sub(r'\s*\bpor favor\b\s*', ' ', limpio).strip()


def parse(texto):
    """Devuelve (accion, argumento) si es un comando fijo, o None para que lo resuelva la IA."""
    t = normalizar(texto)
    for patron, accion in _REGLAS:
        if re.search(patron, t):
            return accion, None
    m = _ABRIR.match(t)
    # Más de 4 palabras o un "y" = pedido compuesto: mejor que lo piense la IA.
    if m and ' y ' not in f' {m["app"]} ' and len(m['app'].split()) <= 4:
        return 'abrir', m['app']
    return None


def buscar_app(nombre, apps):
    """Nombre del menú Inicio que mejor coincide con lo pedido, o None."""
    pedido = re.sub(r'^(?:el|la|los|las) ', '', normalizar(nombre))
    por_nombre = {normalizar(k): k for k in apps}
    if pedido in por_nombre:
        return por_nombre[pedido]
    contienen = [k for n, k in por_nombre.items() if pedido in n]
    if contienen:
        return min(contienen, key=len)  # "chrome" -> "Google Chrome", no "Chrome Remote Desktop"
    parecidos = difflib.get_close_matches(pedido, list(por_nombre), n=1, cutoff=0.6)
    return por_nombre[parecidos[0]] if parecidos else None


_apps = None


def apps_instaladas():
    """Nombre -> AppID de todo lo del menú Inicio, incluidas las apps de la Store (Calculadora, etc.)."""
    global _apps
    if _apps is None:
        cmd = '[Console]::OutputEncoding=[Text.Encoding]::UTF8; @(Get-StartApps) | ConvertTo-Json -Compress'
        salida = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True,
                                timeout=60, creationflags=subprocess.CREATE_NO_WINDOW).stdout.decode('utf-8')
        _apps = {a['Name']: a['AppID'] for a in json.loads(salida)}
    return _apps


def abrir_app(nombre):
    """Abre una app del menú Inicio. Sin simular teclado ni mouse, y nada fuera del menú Inicio."""
    apps = apps_instaladas()
    encontrada = buscar_app(nombre, apps)
    if not encontrada:
        return f'No encontré {nombre} en el menú Inicio.'
    subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{apps[encontrada]}'])
    return f'Abriendo {encontrada}.'


_OPERACIONES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
                ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
                ast.USub: operator.neg, ast.UAdd: operator.pos}


def calcular(expresion):
    """Cuenta exacta para la IA (los modelos chicos erran cuentas). Solo números y + - * / ** % //; nada de eval."""
    def valor(nodo):
        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            return nodo.value
        if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERACIONES:
            izq, der = valor(nodo.left), valor(nodo.right)
            if isinstance(nodo.op, ast.Pow) and abs(der) > 100:
                raise ValueError('potencia demasiado grande')
            return _OPERACIONES[type(nodo.op)](izq, der)
        if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERACIONES:
            return _OPERACIONES[type(nodo.op)](valor(nodo.operand))
        raise ValueError('solo se permiten números y + - * / ** % //')

    try:
        r = valor(ast.parse(expresion.replace(',', '.').replace('x', '*').replace('^', '**'), mode='eval').body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as e:
        return f'No pude calcular {expresion!r}: {e}'
    return str(round(r, 6)).removesuffix('.0') if isinstance(r, float) else str(r)


def ejecutar_local(accion, ahora=None):
    """Ejecuta una acción local y devuelve lo que Vloomy dice."""
    if accion in VK:
        user32 = ctypes.windll.user32
        for _ in range(5 if accion.startswith('volumen') else 1):  # 5 toques = ~10% de volumen
            user32.keybd_event(VK[accion], 0, 0, 0)
            user32.keybd_event(VK[accion], 0, 2, 0)  # 2 = KEYEVENTF_KEYUP
        return 'Listo.'
    if accion == 'bloquear':
        ctypes.windll.user32.LockWorkStation()
        return 'Bloqueada.'
    ahora = ahora or datetime.datetime.now()
    if accion == 'hora':
        return f'Son las {ahora:%H:%M}.'
    if accion == 'fecha':
        return f'Hoy es {_DIAS[ahora.weekday()]} {ahora.day} de {_MESES[ahora.month - 1]}.'
    raise ValueError(f'acción desconocida: {accion}')
