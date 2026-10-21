"""Textos informativos sobre los algoritmos (tabla de complejidades)."""

from typing import NamedTuple


class InfoAlgoritmo(NamedTuple):
    """Fila de la tabla informativa."""

    algoritmo: str
    funcionamiento: str
    complejidad_temporal: str
    complejidad_espacial: str
    estructuras: str
    uso_estructuras: str


INFORMACION_ALGORITMOS: list[InfoAlgoritmo] = [
    InfoAlgoritmo(
        "BFS",
        "Encuentra la ruta con menor cantidad de aristas cuando todas las "
        "conexiones tienen el mismo costo.",
        "O(V+E)",
        "O(V)",
        "dict de adyacencia, deque, dict de predecesores",
        "deque permite extraer el primero en O(1); los diccionarios registran "
        "visitados y predecesores.",
    ),
    InfoAlgoritmo(
        "Dijkstra",
        "Encuentra la ruta de menor costo con pesos no negativos.",
        "O((V+E) log V), con listas de adyacencia y un heap binario.",
        "O(V)",
        "dict de adyacencia, heapq, dict de distancias, set, "
        "dict de predecesores",
        "heapq extrae la menor prioridad en O(log V); dict ofrece acceso "
        "promedio O(1) y set evita procesar nodos cerrados.",
    ),
    InfoAlgoritmo(
        "A*",
        "Busca una ruta de menor costo utilizando una heurística.",
        "Depende de la heurística y del grafo.",
        "O(V) en el peor caso",
        "dict de adyacencia, heapq, dict de costos, set, dict de predecesores",
        "heapq prioriza g(n)+h(n); dict conserva el mejor costo y los "
        "predecesores, y set registra nodos cerrados.",
    ),
]
