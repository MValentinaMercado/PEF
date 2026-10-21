"""Ejecución de herramientas externas como módulos de Python."""

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
