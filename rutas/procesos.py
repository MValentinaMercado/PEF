"""Ejecución de herramientas externas como módulos de Python."""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ejecutar_modulo(
    modulo: str,
    *argumentos: str,
    tiempo: int,
    entorno: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Corre ``python -m modulo`` en la raíz del proyecto, sin ``shell``.

    Usa el mismo intérprete que la aplicación, así encuentra las herramientas
    instaladas en su entorno. Lanza ``RuntimeError`` si pasan ``tiempo``
    segundos sin que termine.

    >>> "Zen of Python" in ejecutar_modulo("this", tiempo=30).stdout
    True
    """
    try:
        return subprocess.run(
            [sys.executable, "-m", modulo, *argumentos],
            cwd=RAIZ,
            env=entorno,
            capture_output=True,
            text=True,
            timeout=tiempo,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"{modulo} tardó demasiado.") from error


def ruta_relativa(ruta: str) -> str:
    """Ruta relativa a la raíz del proyecto, con ``/`` en cualquier sistema.

    >>> ruta_relativa("api/app.py")
    'api/app.py'
    >>> ruta_relativa(str(RAIZ / "rutas" / "grafo.py"))
    'rutas/grafo.py'
    """
    try:
        return Path(ruta).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return Path(ruta).as_posix()


def entorno_cobertura() -> dict[str, str]:
    """Entorno para medir cobertura sin chocar con ``memory_profiler``.

    ``coverage`` usa ``sys.monitoring`` (Python 3.12+) en vez de
    ``sys.settrace``; así no interfiere con los perfiladores.
    """
    return {**os.environ, "COVERAGE_CORE": "sysmon"}
