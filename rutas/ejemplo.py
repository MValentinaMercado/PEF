"""Grafo de ejemplo donde BFS y Dijkstra devuelven rutas distintas."""

from rutas.grafo import Grafo

EJEMPLO_NODOS = (
    ("A", 80, 200),
    ("B", 250, 80),
    ("C", 250, 320),
    ("D", 450, 110),
    ("E", 450, 300),
    ("F", 700, 200),
)
EJEMPLO_ARISTAS = (
    ("A", "B", 160),
    ("A", "C", 80),
    ("B", "C", 40),
    ("B", "D", 200),
    ("C", "D", 320),
    ("C", "E", 400),
    ("D", "E", 80),
    ("D", "F", 240),
    ("E", "F", 120),
)


def crear_grafo_ejemplo() -> Grafo:
    """Construye el grafo de 6 nodos y 9 aristas.

    >>> g = crear_grafo_ejemplo()
    >>> len(g.nodos()), sum(len(v) for v in g.adyacencia.values()) // 2
    (6, 9)
    """
    grafo = Grafo()
    for nombre, x, y in EJEMPLO_NODOS:
        grafo.agregar_nodo(nombre, x, y)
    for a, b, peso in EJEMPLO_ARISTAS:
        grafo.conectar(a, b, peso)
    return grafo
