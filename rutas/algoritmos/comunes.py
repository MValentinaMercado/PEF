"""Tipos y utilidades compartidas por los algoritmos de rutas."""

import heapq
import math
from collections.abc import Callable
from typing import NamedTuple

from rutas.grafo import Grafo


class ResultadoBusqueda(NamedTuple):
    """Resultado común: ruta, distancia acumulada y nodos explorados."""

    ruta: list[str] | None
    distancia: float
    nodos_explorados: int


def reconstruir_ruta(
    anterior: dict[str, str | None], destino: str
) -> list[str]:
    """Reconstruye el camino siguiendo los predecesores desde el destino."""
    ruta = []
    nodo: str | None = destino
    while nodo is not None:
        ruta.append(nodo)
        nodo = anterior[nodo]
    return ruta[::-1]


def calcular_distancia(grafo: Grafo, ruta: list[str]) -> float:
    """Suma los pesos de las aristas de la ruta."""
    return sum(
        grafo.adyacencia[a][b] for a, b in zip(ruta, ruta[1:], strict=False)
    )


def buscar_con_heap(
    grafo: Grafo,
    origen: str,
    destino: str,
    heuristica: Callable[[str], float] | None = None,
) -> ResultadoBusqueda:
    """Búsqueda de menor costo con heap: Dijkstra, o A* si hay heurística.

    El heap guarda ``(prioridad, costo, nodo)``. Sin heurística la prioridad
    es el costo acumulado g(n) (Dijkstra); con heurística es g(n) + h(n)
    (A*). Es el único lugar donde está el bucle, y se evita llamar a una
    función por nodo cuando no hay heurística: es el camino caliente y esa
    llamada lo hacía más lento.
    """
    costo = {origen: 0.0}
    anterior: dict[str, str | None] = {origen: None}
    cerrados = set()
    heap = [(0.0 if heuristica is None else heuristica(origen), 0.0, origen)]
    explorados = 0
    while heap:
        _, costo_actual, actual = heapq.heappop(heap)
        if actual in cerrados:  # ignora entradas antiguas
            continue
        cerrados.add(actual)
        explorados += 1
        if actual == destino:
            ruta = reconstruir_ruta(anterior, destino)
            return ResultadoBusqueda(ruta, costo_actual, explorados)
        for vecino, peso in grafo.vecinos_habilitados(actual):
            nuevo_costo = costo_actual + peso
            if nuevo_costo < costo.get(vecino, math.inf):
                costo[vecino] = nuevo_costo
                anterior[vecino] = actual
                prioridad = (
                    nuevo_costo
                    if heuristica is None
                    else nuevo_costo + heuristica(vecino)
                )
                heapq.heappush(heap, (prioridad, nuevo_costo, vecino))
    return ResultadoBusqueda(None, math.inf, explorados)
