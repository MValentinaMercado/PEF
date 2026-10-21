"""Servidor SnakeViz que muestra los perfiles ``.prof`` de cProfile.

SnakeViz es una herramienta aparte (``snakeviz archivo.prof``): levanta su
propio servidor web. Aquí se lanza en segundo plano, solo en la máquina
local, y la ventana de análisis lo incrusta con un ``<iframe>``.
"""

import atexit
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PERFILES = RAIZ / "perfiles"
PUERTO = 8081
HOST = "127.0.0.1"


@dataclass
class _Servidor:
    """Proceso de SnakeViz lanzado por esta aplicación (si hay uno)."""

    proceso: subprocess.Popen | None = None


_servidor = _Servidor()


def _escuchando() -> bool:
    """Indica si algo atiende en el puerto de SnakeViz."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexion:
        conexion.settimeout(0.2)
        return conexion.connect_ex((HOST, PUERTO)) == 0


def url_perfil(archivo: Path) -> str:
    """Dirección que SnakeViz usa para mostrar un ``.prof``.

    La ruta va codificada en un solo segmento (sin ``/``), en Linux y Windows:

    >>> url = url_perfil(Path("x.prof"))
    >>> url.startswith("http://127.0.0.1:8081/snakeviz/")
    True
    >>> url.endswith("x.prof")
    True
    >>> "/" in url.split("/snakeviz/")[1]
    False
    """
    ruta = quote(str(archivo.resolve()), safe="")
    return f"http://{HOST}:{PUERTO}/snakeviz/{ruta}"


def iniciar(archivo: Path) -> None:
    """Arranca SnakeViz si todavía no está corriendo.

    Lanza ``RuntimeError`` si el servidor no responde a tiempo.
    """
    actual = _servidor.proceso
    if actual is not None and actual.poll() is None and _escuchando():
        return
    detener()
    # El proceso debe seguir vivo después de esta función: no cabe un ``with``.
    proceso = subprocess.Popen(  # pylint: disable=consider-using-with
        [
            sys.executable,
            "-m",
            "snakeviz",
            "-s",
            "-H",
            HOST,
            "-p",
            str(PUERTO),
            str(archivo),
        ],
        cwd=RAIZ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _servidor.proceso = proceso
    limite = time.monotonic() + 10
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            break
        if _escuchando():
            return
        time.sleep(0.1)
    detener()
    raise RuntimeError("SnakeViz no pudo iniciarse (¿está instalado?).")


def detener() -> None:
    """Cierra el servidor de SnakeViz si lo lanzó esta aplicación."""
    proceso = _servidor.proceso
    if proceso is not None and proceso.poll() is None:
        proceso.terminate()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
    _servidor.proceso = None


atexit.register(detener)
