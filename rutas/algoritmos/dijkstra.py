"""Algoritmo de Dijkstra optimizado con heap binario."""

from rutas.grafo import Grafo

from .comunes import ResultadoBusqueda, buscar_con_heap


def dijkstra(grafo: Grafo, origen: str, destino: str) -> ResultadoBusqueda:
    """Ruta de menor costo con pesos no negativos.

    Tiempo O((V+E) log V), espacio O(V). El bucle está en
    :func:`~rutas.algoritmos.comunes.buscar_con_heap`, compartido con A*:
    aquí la prioridad es solo el costo acumulado.
    """
    return buscar_con_heap(grafo, origen, destino)
