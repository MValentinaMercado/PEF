"""Pruebas de BFS, Dijkstra y A*."""

import math
import unittest

from rutas.algoritmos import a_estrella, bfs, dijkstra
from rutas.generador import generar_consultas, generar_grafo
from rutas.grafo import Grafo


def construir_grafo_ejemplo() -> Grafo:
    """Grafo donde el camino con menos saltos NO es el de menor costo."""
    grafo = Grafo()
    posiciones = {"A": (0, 0), "B": (1, 0), "C": (2, 0), "D": (3, 0)}
    for nombre, (x, y) in posiciones.items():
        grafo.agregar_nodo(nombre, x, y)
    grafo.conectar("A", "D", 10)
    grafo.conectar("A", "B", 1)
    grafo.conectar("B", "C", 1)
    grafo.conectar("C", "D", 1)
    return grafo


class PruebasAlgoritmos(unittest.TestCase):
    """Verifica rutas, costos y bloqueos."""

    def test_bfs_minimiza_saltos(self):
        resultado = bfs(construir_grafo_ejemplo(), "A", "D")
        self.assertEqual(resultado.ruta, ["A", "D"])
        self.assertEqual(resultado.distancia, 10)

    def test_dijkstra_minimiza_costo(self):
        resultado = dijkstra(construir_grafo_ejemplo(), "A", "D")
        self.assertEqual(resultado.ruta, ["A", "B", "C", "D"])
        self.assertEqual(resultado.distancia, 3)

    def test_bloqueo_fuerza_otra_ruta(self):
        grafo = construir_grafo_ejemplo()
        grafo.establecer_bloqueo("A", "D", True)
        self.assertEqual(bfs(grafo, "A", "D").ruta, ["A", "B", "C", "D"])
        grafo.establecer_bloqueo("B", "C", True)
        self.assertIsNone(dijkstra(grafo, "A", "D").ruta)
        self.assertEqual(dijkstra(grafo, "A", "D").distancia, math.inf)

    def test_a_estrella_igual_a_dijkstra(self):
        grafo = generar_grafo(300)
        for origen, destino in generar_consultas(grafo, 20):
            esperado = dijkstra(grafo, origen, destino).distancia
            obtenido = a_estrella(grafo, origen, destino).distancia
            self.assertAlmostEqual(esperado, obtenido, places=6)


if __name__ == "__main__":
    unittest.main()
