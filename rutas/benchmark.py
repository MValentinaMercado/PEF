"""Benchmark real de BFS, Dijkstra y A* con grafos de distintos tamaños."""

from collections.abc import Sequence
from typing import NamedTuple

from rutas.algoritmos import ALGORITMOS
from rutas.generador import generar_consultas, generar_grafo
from rutas.grafo import Grafo
from rutas.mediciones import medir_consulta

TAMANOS_GRAFO = (100, 1000, 5000)
CONSULTAS_POR_TAMANO = 10


class FilaBenchmark(NamedTuple):
    """Promedios de un algoritmo sobre un grafo de cierto tamaño."""

    nodos: int
    algoritmo: str
    tiempo_ms: float
    memoria_kb: float
    nodos_explorados: float


def medir_algoritmos(grafo: Grafo, consultas: int) -> list[FilaBenchmark]:
    """Mide cada algoritmo sobre las mismas consultas de un grafo."""
    grafo.factor_heuristica()  # se calcula antes para no sesgar a A*
    pares = generar_consultas(grafo, consultas)
    filas = []
    for nombre, algoritmo in ALGORITMOS.items():
        medidas = [
            medir_consulta(algoritmo, grafo, origen, destino)
            for origen, destino in pares
        ]
        filas.append(
            FilaBenchmark(
                len(grafo.adyacencia),
                nombre,
                sum(m.tiempo_ms for m in medidas) / consultas,
                sum(m.memoria_kb for m in medidas) / consultas,
                sum(m.nodos_explorados for m in medidas) / consultas,
            )
        )
    return filas


def ejecutar_benchmark(
    tamanos: Sequence[int] = TAMANOS_GRAFO,
    consultas: int = CONSULTAS_POR_TAMANO,
) -> list[FilaBenchmark]:
    """Mide cada algoritmo sobre las mismas consultas de cada grafo."""
    filas: list[FilaBenchmark] = []
    for cantidad_nodos in tamanos:
        filas.extend(
            medir_algoritmos(generar_grafo(cantidad_nodos), consultas)
        )
    return filas
