"""Búsqueda en anchura (BFS)."""

import math
from collections import deque

from rutas.grafo import Grafo

from .comunes import ResultadoBusqueda, calcular_distancia, reconstruir_ruta


def bfs(grafo: Grafo, origen: str, destino: str) -> ResultadoBusqueda:
    """Busca una ruta con menor cantidad de aristas. O(V+E), espacio O(V).

    BFS minimiza saltos, no la distancia ponderada. Usa deque para que
    extraer el primer elemento de la cola cueste O(1).
    """
    anterior: dict[str, str | None] = {origen: None}
    cola = deque([origen])
    explorados = 0
    while cola:
        actual = cola.popleft()
        explorados += 1
        if actual == destino:
            ruta = reconstruir_ruta(anterior, destino)
            return ResultadoBusqueda(
                ruta, calcular_distancia(grafo, ruta), explorados
            )
        for vecino, _ in grafo.vecinos_habilitados(actual):
            if vecino not in anterior:
                anterior[vecino] = actual
                cola.append(vecino)
    return ResultadoBusqueda(None, math.inf, explorados)
