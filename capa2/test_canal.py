"""Prueba del canal de la capa 2 sin Claude: hace de Claude Code hablando MCP por stdio con canal.mjs.

Correr:  ..\\voice\\.venv\\Scripts\\python.exe test_canal.py
"""
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).parent
PUERTO, TOKEN = 8798, 'token-de-prueba'
proc = subprocess.Popen(['node', 'canal.mjs'], cwd=AQUI, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        env={**os.environ, 'VLOOMY_TOKEN': TOKEN, 'VLOOMY_CANAL_PUERTO': str(PUERTO)},
                        text=True, encoding='utf-8')


def enviar(mensaje):
    proc.stdin.write(json.dumps(mensaje) + '\n')
    proc.stdin.flush()


def recibir():
    return json.loads(proc.stdout.readline())


def http(ruta, datos=None, token=TOKEN):
    req = urllib.request.Request(f'http://127.0.0.1:{PUERTO}{ruta}', method='GET' if datos is None else 'POST',
                                 data=None if datos is None else json.dumps(datos).encode(),
                                 headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ''


try:
    enviar({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
        'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'prueba', 'version': '0'}}})
    capacidades = recibir()['result']['capabilities']
    assert 'claude/channel' in capacidades['experimental'] and 'claude/channel/permission' in capacidades['experimental']
    enviar({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    time.sleep(0.5)

    assert http('/tarea', {'texto': 'hola'}, token='otro')[0] == 401

    eventos = []
    req = urllib.request.Request(f'http://127.0.0.1:{PUERTO}/eventos', headers={'Authorization': f'Bearer {TOKEN}'})
    flujo = urllib.request.urlopen(req)
    threading.Thread(target=lambda: [eventos.append(json.loads(l)) for l in flujo], daemon=True).start()

    # Vloomy manda una tarea -> Claude Code la recibe como evento del canal
    assert http('/tarea', {'texto': 'buscá vuelos a Córdoba'}) == (200, '{"id":"1"}')
    evento = recibir()
    assert evento['method'] == 'notifications/claude/channel', evento
    assert evento['params'] == {'content': 'buscá vuelos a Córdoba', 'meta': {'id': '1'}}

    # Claude responde con la herramienta -> Vloomy lo recibe por /eventos
    enviar({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'responder', 'arguments': {'id': '1', 'texto': 'Encontré tres vuelos.'}}})
    assert recibir()['result']['content'][0]['text'] == 'entregado'

    # Claude Code pide permiso -> Vloomy lo recibe, decide y manda el veredicto
    enviar({'jsonrpc': '2.0', 'method': 'notifications/claude/channel/permission_request', 'params': {
        'request_id': 'abcde', 'tool_name': 'Bash', 'description': 'Listar archivos', 'input_preview': '{}'}})
    time.sleep(0.5)
    assert http('/veredicto', {'request_id': 'abcde', 'permitir': True})[0] == 200
    veredicto = recibir()
    assert veredicto == {'jsonrpc': '2.0', 'method': 'notifications/claude/channel/permission',
                         'params': {'request_id': 'abcde', 'behavior': 'allow'}}, veredicto
    assert http('/veredicto', {'request_id': 'x; rm', 'permitir': True})[0] == 400

    time.sleep(0.3)
    assert eventos == [{'tipo': 'conectado'}, {'tipo': 'respuesta', 'id': '1', 'texto': 'Encontré tres vuelos.'},
                       {'tipo': 'permiso', 'request_id': 'abcde', 'tool_name': 'Bash',
                        'description': 'Listar archivos', 'input_preview': '{}'}], eventos
    print('ok: canal de la capa 2')
finally:
    proc.kill()
