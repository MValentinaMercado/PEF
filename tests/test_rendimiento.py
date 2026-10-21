"""Pruebas de rendimiento con ``timeit`` (clase de testing)."""

import timeit

from rutas.algoritmos import a_estrella, bfs, dijkstra
from rutas.cache import CacheRutas
from rutas.generador import generar_consultas, generar_grafo


def test_cache_acelera_consultas_repetidas():
    grafo = generar_grafo(1000)
    origen, destino = generar_consultas(grafo, 1)[0]
    cache = CacheRutas()
    sin = timeit.timeit(lambda: dijkstra(grafo, origen, destino), number=50)
    con = timeit.timeit(
        lambda: cache.consultar(grafo, origen, destino), number=50
    )
    assert con < sin


def test_bfs_es_mas_barato_que_dijkstra():
    grafo = generar_grafo(2000)
    origen, destino = generar_consultas(grafo, 1)[0]
    t_bfs = min(
        timeit.repeat(lambda: bfs(grafo, origen, destino), number=5, repeat=3)
    )
    t_dij = min(
        timeit.repeat(
            lambda: dijkstra(grafo, origen, destino), number=5, repeat=3
        )
    )
    assert t_bfs < t_dij * 1.5  # margen para el ruido de la medición


def test_a_estrella_no_empeora_el_resultado():
    grafo = generar_grafo(500)
    for origen, destino in generar_consultas(grafo, 10):
        assert (
            abs(
                a_estrella(grafo, origen, destino).distancia
                - dijkstra(grafo, origen, destino).distancia
            )
            < 1e-6
        )
