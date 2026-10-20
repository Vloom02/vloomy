"""Mecánica del modo mejora sobre un repo git de juguete (sin Claude ni red).

Correr:  .venv\\Scripts\\python.exe test_mejora.py
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path

import vloomy as V


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def preparar_mejora(repo, nombre, contenido):
    """Hace lo que deja hacer_mejora: una copia (worktree) con un commit 'Mejora:'."""
    copia = repo / '.mejoras' / nombre
    git(repo, 'worktree', 'add', '-q', '-b', nombre, str(copia), 'HEAD')
    (copia / 'saludo.txt').write_text(contenido)
    git(copia, 'commit', '-qam', f'Mejora: {contenido}', '-m', f'Cambié el saludo a {contenido}.')
    return copia


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, 'init', '-q', '-b', 'main')
        git(repo, 'config', 'user.email', 'prueba@vloomy')
        git(repo, 'config', 'user.name', 'Prueba')
        (repo / '.gitignore').write_text('.mejoras/\n')
        (repo / 'saludo.txt').write_text('hola')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-qm', 'inicio')

        v = V.Vloomy()
        v.repo = repo
        reinicios = []

        async def sin_reiniciar():
            reinicios.append(True)

        v.reiniciar = sin_reiniciar

        # Sin mejora lista, nada que aplicar ni descartar.
        assert 'No hay ninguna' in await v.aplicar_mejora()
        assert 'No hay ninguna' in await v.descartar_mejora()

        # Retomar al arrancar: encuentra la copia lista.
        copia = preparar_mejora(repo, 'mejora-1', 'buen día')
        await v.restaurar_mejora()
        assert v.mejora and v.mejora['nombre'] == 'mejora-1', v.mejora

        # Aplicar: el código principal queda con el cambio, la copia y la rama desaparecen, y pide reiniciar.
        respuesta = await v.aplicar_mejora()
        await asyncio.sleep(0)
        assert respuesta.startswith('Apliqué'), respuesta
        assert (repo / 'saludo.txt').read_text() == 'buen día'
        assert not copia.exists() and 'mejora-1' not in git(repo, 'branch')
        assert v.mejora is None and reinicios

        # Deshacer: vuelve al saludo anterior con un commit nuevo.
        respuesta = await v.deshacer_mejora()
        assert respuesta.startswith('Deshice'), respuesta
        assert (repo / 'saludo.txt').read_text() == 'hola'
        assert 'no deshice' in (await v.deshacer_mejora())  # lo último ya no es una mejora

        # Descartar: el código principal no cambia.
        copia = preparar_mejora(repo, 'mejora-2', 'chau')
        await v.restaurar_mejora()
        assert (await v.descartar_mejora()).startswith('Listo')
        assert (repo / 'saludo.txt').read_text() == 'hola' and not copia.exists()

        # Una copia a medio hacer (sin commit propio) se borra al arrancar.
        git(repo, 'worktree', 'add', '-q', '-b', 'mejora-3', str(repo / '.mejoras' / 'mejora-3'), 'HEAD')
        await v.restaurar_mejora()
        assert v.mejora is None and not (repo / '.mejoras' / 'mejora-3').exists()

        # No pisa cambios sin guardar del código principal.
        preparar_mejora(repo, 'mejora-4', 'hey')
        await v.restaurar_mejora()
        (repo / 'saludo.txt').write_text('editado a mano')
        assert 'sin guardar' in await v.aplicar_mejora()
        git(repo, 'checkout', '--', 'saludo.txt')
        assert (await v.descartar_mejora()).startswith('Listo')
        git(repo, 'worktree', 'prune')
    print('ok: modo mejora')

asyncio.run(main())
