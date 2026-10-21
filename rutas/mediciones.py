"""Utilidades para medir tiempo y memoria de forma real."""

import time
import tracemalloc
from collections.abc import Callable
from typing import NamedTuple, TypeVar

from rutas.algoritmos import Algoritmo
from rutas.grafo import Grafo

T = TypeVar("T")
BYTES_POR_KB = 1024


class Medicion(NamedTuple):
    """Resultado medido de una consulta de ruta."""

    ruta: list[str] | None
    distancia: float
    tiempo_ms: float
    memoria_kb: float
    nodos_explorados: int


def medir_tiempo_y_memoria(funcion: Callable[[], T]) -> tuple[float, float, T]:
    """Ejecuta ``funcion`` dos veces y devuelve ``(ms, KB, resultado)``.

    El tiempo se toma en una corrida limpia y el pico de memoria en otra
    con ``tracemalloc``, que enlentece la ejecución y falsearía el tiempo.
    """
    inicio = time.perf_counter()
    resultado = funcion()
    tiempo_ms = (time.perf_counter() - inicio) * 1000
    tracemalloc.start()
    funcion()
    pico_bytes = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return tiempo_ms, pico_bytes / BYTES_POR_KB, resultado


def medir_consulta(
    algoritmo: Algoritmo,
    grafo: Grafo,
    origen: str,
    destino: str,
    repeticiones: int = 1,
) -> Medicion:
    """Mide una consulta; el tiempo es el promedio de ``repeticiones``."""
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        resultado = algoritmo(grafo, origen, destino)
    tiempo_ms = (time.perf_counter() - inicio) * 1000 / repeticiones
    tracemalloc.start()
    algoritmo(grafo, origen, destino)
    pico_bytes = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return Medicion(
        resultado.ruta,
        resultado.distancia,
        tiempo_ms,
        pico_bytes / BYTES_POR_KB,
        resultado.nodos_explorados,
    )
