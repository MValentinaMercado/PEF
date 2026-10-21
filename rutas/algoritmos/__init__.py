"""API pública unificada para los algoritmos de búsqueda."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from rutas.grafo import Grafo

from .a_estrella import a_estrella
from .bfs import bfs
from .comunes import ResultadoBusqueda, calcular_distancia
from .dijkstra import dijkstra

if TYPE_CHECKING:
    Algoritmo = Callable[[Grafo, str, str], ResultadoBusqueda]
else:
    Algoritmo = Callable

ALGORITMOS: dict[str, Algoritmo] = {
    "BFS": bfs,
    "Dijkstra": dijkstra,
    "A*": a_estrella,
}

__all__ = [
    "ResultadoBusqueda",
    "Algoritmo",
    "ALGORITMOS",
    "bfs",
    "dijkstra",
    "a_estrella",
    "calcular_distancia",
]
