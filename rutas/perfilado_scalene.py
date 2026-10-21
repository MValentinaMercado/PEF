"""Perfilado con Scalene: CPU (Python, nativo y sistema) y memoria por línea.

Scalene perfila un programa entero, por eso se ejecuta como proceso aparte
sobre :mod:`rutas.escenario_scalene` y después se lee el JSON que genera.
Se necesita Scalene 2.0 o superior (``scalene run``).
"""

import json
import os
import tempfile
from pathlib import Path
from typing import NamedTuple

from rutas.procesos import RAIZ, ejecutar_modulo

ESCENARIO = Path(__file__).resolve().parent / "escenario_scalene.py"
TIEMPO_MAXIMO_S = 180
MINIMO_CPU = 0.5  # % del tiempo total para mostrar una línea
MINIMO_MEMORIA_MB = 1.0
# Scalene escribe estos caracteres como secuencias \\uXXXX dentro del texto.
ESCAPES = {"\\u003c": "<", "\\u003e": ">", "\\u0026": "&"}


class FilaScalene(NamedTuple):
    """Una línea de código según Scalene."""

    archivo: str
    linea: int
    cpu_python: float  # % del tiempo total en código Python
    cpu_nativo: float  # % del tiempo total en código nativo (C)
    sistema: float  # % del tiempo total en llamadas al sistema
    memoria_pico_mb: float
    codigo: str


class ResultadoScalene(NamedTuple):
    """Resumen del programa y sus líneas más costosas."""

    segundos: float
    memoria_pico_mb: float
    fraccion_python: float  # de la memoria máxima, cuánta es de Python
    filas: list[FilaScalene]


def _sin_escapes(texto: str) -> str:
    r"""Revierte el escape de ``<``, ``>`` y ``&`` que hace Scalene.

    >>> _sin_escapes(r"if a \u003c b \u0026 c:")
    'if a < b & c:'
    """
    for escape, caracter in ESCAPES.items():
        texto = texto.replace(escape, caracter)
    return texto


def resumir_scalene(texto_json: str, cantidad: int = 12) -> ResultadoScalene:
    """Las líneas del proyecto con más CPU (o memoria) según Scalene.

    Se descartan el propio escenario y todo lo que no sea del proyecto.

    >>> linea = {"lineno": 7, "line": "x = 1\\n", "n_cpu_percent_python": 40.0,
    ...          "n_cpu_percent_c": 5.0, "n_sys_percent": 0.0,
    ...          "n_peak_mb": 2.5}
    >>> archivo = str(RAIZ / "rutas" / "a.py")
    >>> datos = {"elapsed_time_sec": 3.0, "max_footprint_mb": 9.0,
    ...          "max_footprint_python_fraction": 0.9,
    ...          "files": {archivo: {"lines": [linea]},
    ...                    "/otro/b.py": {"lines": [linea]}}}
    >>> r = resumir_scalene(json.dumps(datos))
    >>> [(f.archivo, f.linea, f.codigo) for f in r.filas]
    [('rutas/a.py', 7, 'x = 1')]
    >>> r.segundos, r.memoria_pico_mb
    (3.0, 9.0)
    """
    datos = json.loads(texto_json)
    filas = []
    for archivo, info in datos["files"].items():
        ruta = Path(archivo)
        if ruta == ESCENARIO or not ruta.is_relative_to(RAIZ):
            continue
        for linea in info["lines"]:
            cpu = (
                linea["n_cpu_percent_python"]
                + linea["n_cpu_percent_c"]
                + linea["n_sys_percent"]
            )
            if cpu >= MINIMO_CPU or linea["n_peak_mb"] >= MINIMO_MEMORIA_MB:
                filas.append(
                    FilaScalene(
                        ruta.relative_to(RAIZ).as_posix(),
                        linea["lineno"],
                        linea["n_cpu_percent_python"],
                        linea["n_cpu_percent_c"],
                        linea["n_sys_percent"],
                        linea["n_peak_mb"],
                        _sin_escapes(linea["line"]).strip(),
                    )
                )
    filas.sort(
        key=lambda f: (
            -(f.cpu_python + f.cpu_nativo + f.sistema),
            -f.memoria_pico_mb,
        )
    )
    return ResultadoScalene(
        datos["elapsed_time_sec"],
        datos["max_footprint_mb"],
        datos["max_footprint_python_fraction"],
        filas[:cantidad],
    )


def ejecutar_scalene() -> ResultadoScalene:
    """Perfila el escenario con ``scalene run`` y resume el resultado.

    Lanza ``RuntimeError`` si Scalene no está instalado, tarda demasiado o
    no logra generar el perfil (por ejemplo, en sistemas donde no puede medir
    memoria).
    """
    with tempfile.TemporaryDirectory() as carpeta:
        perfil = Path(carpeta) / "scalene.json"
        proceso = ejecutar_modulo(
            "scalene",
            "run",
            "-o",
            str(perfil),
            str(ESCENARIO),
            tiempo=TIEMPO_MAXIMO_S,
            # Para que el escenario pueda hacer ``from rutas import ...``.
            entorno={**os.environ, "PYTHONPATH": str(RAIZ)},
        )
        if not perfil.exists():
            raise RuntimeError(
                "Scalene no generó el perfil (¿está instalado scalene>=2.0?): "
                + (proceso.stderr or proceso.stdout)[-500:]
            )
        return resumir_scalene(perfil.read_text(encoding="utf-8"))
