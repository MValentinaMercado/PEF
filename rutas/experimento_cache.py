"""Experimento de caching: consultas con y sin caché."""

import random
from typing import NamedTuple

from rutas.algoritmos import dijkstra
from rutas.cache import CacheRutas
from rutas.generador import generar_consultas, generar_grafo
from rutas.mediciones import medir_tiempo_y_memoria


class ResultadoCache(NamedTuple):
    """Comparación con/sin caché y comprobación de la invalidación."""

    total_consultas: int
    pares_distintos: int
    sin_cache: tuple[float, float]  # (ms, KB)
    con_cache: tuple[float, float]  # (ms, KB)
    aciertos: int
    fallos: int
    invalidaciones: int
    fallo_tras_cambio: bool
    acierto_al_repetir: bool


def ejecutar_experimento_cache(
    cantidad_nodos: int = 2000,
    total_consultas: int = 500,
    pares_distintos: int = 50,
) -> ResultadoCache:
    """Repite consultas sobre pocos pares para mostrar el efecto de la caché.

    Al final modifica el grafo y verifica que la caché se invalide.
    """
    grafo = generar_grafo(cantidad_nodos, semilla=5)
    unicos = generar_consultas(grafo, pares_distintos, semilla=1)
    azar = random.Random(2)  # semilla fija: carga reproducible, no criptografía
    carga = [azar.choice(unicos) for _ in range(total_consultas)]  # NOSONAR

    def sin_cache() -> None:
        for origen, destino in carga:
            dijkstra(grafo, origen, destino)

    def con_cache() -> CacheRutas:
        cache = CacheRutas()
        for origen, destino in carga:
            cache.consultar(grafo, origen, destino)
        return cache

    ms_sin, kb_sin, _ = medir_tiempo_y_memoria(sin_cache)
    ms_con, kb_con, cache = medir_tiempo_y_memoria(con_cache)

    aciertos, fallos = cache.aciertos, cache.fallos
    nodos = grafo.nodos()
    grafo.conectar(nodos[0], nodos[-1], 1.0)  # el grafo cambia
    cache.consultar(grafo, *carga[0])
    fallo_tras_cambio = cache.fallos == fallos + 1
    cache.consultar(grafo, *carga[0])
    acierto_al_repetir = cache.aciertos == aciertos + 1
    return ResultadoCache(
        total_consultas,
        pares_distintos,
        (ms_sin, kb_sin),
        (ms_con, kb_con),
        aciertos,
        fallos,
        cache.invalidaciones,
        fallo_tras_cambio,
        acierto_al_repetir,
    )
