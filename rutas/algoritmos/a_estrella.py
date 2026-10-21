"""Algoritmo A* con heurística euclídea escalada."""

import math

from rutas.grafo import Grafo

from .comunes import ResultadoBusqueda, buscar_con_heap


def a_estrella(grafo: Grafo, origen: str, destino: str) -> ResultadoBusqueda:
    """Busca una ruta guiada por f(n)=g(n)+h(n).

    La complejidad depende de la heurística y del grafo; en el peor caso
    puede explorar gran parte de la red. El bucle está en
    :func:`~rutas.algoritmos.comunes.buscar_con_heap`, compartido con
    Dijkstra: aquí solo se define h(n).
    """
    factor = grafo.factor_heuristica()
    posicion_destino = grafo.posiciones[destino]

    def heuristica(nodo: str) -> float:
        return factor * math.dist(grafo.posiciones[nodo], posicion_destino)

    return buscar_con_heap(grafo, origen, destino, heuristica)
