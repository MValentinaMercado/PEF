"""Escalabilidad de los algoritmos hasta 100.000 nodos frente a la teoría.

Para cada tamaño se mide tiempo y memoria y se compara el tiempo observado
con dos esperados, ambos calculados a partir del tamaño más chico:

* **Esperado teórico**: lo que predice la complejidad en el peor caso,
  O(V + E) para BFS y O((V + E) log V) para Dijkstra y A*.
* **Esperado según nodos explorados**: igual, pero usando los nodos que el
  algoritmo realmente exploró. Las búsquedas terminan al llegar al destino,
  así que el trabajo real depende de cuánto de la red se recorre, no de V.

Un cociente observado/esperado cercano a 1 significa que el algoritmo escala
como dice la teoría; mayor que 1, que algo más (caché de CPU, memoria,
recolector de basura) agrega costo por nodo.
"""

import math
from collections.abc import Sequence
from functools import partial
from typing import NamedTuple

from rutas.benchmark import FilaBenchmark, medir_algoritmos
from rutas.generador import generar_grafo
from rutas.mediciones import medir_tiempo_y_memoria

# (cantidad de nodos, consultas por algoritmo): menos consultas en los
# grafos grandes, donde cada una tarda cientos de milisegundos.
PLAN = ((1_000, 20), (5_000, 20), (10_000, 10), (50_000, 5), (100_000, 5))
KB_POR_MB = 1024


class FilaEscalabilidad(NamedTuple):
    """Una medición y su comparación con la teoría."""

    nodos: int
    aristas: int
    algoritmo: str
    tiempo_ms: float
    memoria_kb: float
    nodos_explorados: float
    us_por_nodo: float  # microsegundos por nodo explorado
    esperado_ms: float  # según la complejidad teórica
    razon: float  # observado / esperado teórico
    esperado_explorados_ms: float  # según los nodos explorados
    razon_explorados: float  # observado / esperado según explorados


class MemoriaGrafo(NamedTuple):
    """Costo de construir y guardar el grafo de cierto tamaño."""

    nodos: int
    aristas: int
    memoria_mb: float
    segundos: float


class ResultadoEscalabilidad(NamedTuple):
    """Filas por algoritmo y tamaño, y memoria de cada grafo."""

    filas: list[FilaEscalabilidad]
    grafos: list[MemoriaGrafo]


def trabajo_teorico(algoritmo: str, nodos: int, aristas: int) -> float:
    """Operaciones que predice la complejidad, salvo una constante.

    >>> trabajo_teorico("BFS", 1000, 3000)
    4000.0
    >>> trabajo_teorico("Dijkstra", 1024, 3000)
    40240.0
    """
    base = nodos + aristas
    return float(base) if algoritmo == "BFS" else base * math.log2(nodos)


def trabajo_explorado(algoritmo: str, nodos: int, explorados: float) -> float:
    """Igual que la teoría, pero sobre los nodos realmente explorados.

    >>> trabajo_explorado("BFS", 1024, 500)
    500.0
    >>> trabajo_explorado("A*", 1024, 500)
    5000.0
    """
    if algoritmo == "BFS":
        return float(explorados)
    return explorados * math.log2(nodos)


def comparar_con_teoria(
    medidas: Sequence[FilaBenchmark], aristas: dict[int, int]
) -> list[FilaEscalabilidad]:
    """Agrega a cada medición los esperados y los cocientes.

    El esperado de cada tamaño se escala desde el más chico del mismo
    algoritmo, que por eso tiene cocientes iguales a 1.

    >>> medidas = [
    ...     FilaBenchmark(1000, "Dijkstra", 1.0, 10.0, 500),
    ...     FilaBenchmark(2000, "Dijkstra", 2.2, 20.0, 1000),
    ... ]
    >>> filas = comparar_con_teoria(medidas, {1000: 3000, 2000: 6000})
    >>> [round(f.razon, 2) for f in filas]
    [1.0, 1.0]
    >>> [round(f.razon_explorados, 2) for f in filas]
    [1.0, 1.0]
    """
    base: dict[str, FilaBenchmark] = {}
    for medida in sorted(medidas, key=lambda m: m.nodos):
        base.setdefault(medida.algoritmo, medida)
    filas = []
    for m in medidas:
        b = base[m.algoritmo]
        esperado = (
            b.tiempo_ms
            * trabajo_teorico(m.algoritmo, m.nodos, aristas[m.nodos])
            / trabajo_teorico(m.algoritmo, b.nodos, aristas[b.nodos])
        )
        esperado_explorados = (
            b.tiempo_ms
            * trabajo_explorado(m.algoritmo, m.nodos, m.nodos_explorados)
            / trabajo_explorado(m.algoritmo, b.nodos, b.nodos_explorados)
        )
        filas.append(
            FilaEscalabilidad(
                m.nodos,
                aristas[m.nodos],
                m.algoritmo,
                m.tiempo_ms,
                m.memoria_kb,
                m.nodos_explorados,
                1000 * m.tiempo_ms / m.nodos_explorados,
                esperado,
                m.tiempo_ms / esperado,
                esperado_explorados,
                m.tiempo_ms / esperado_explorados,
            )
        )
    return filas


def ejecutar_escalabilidad(
    plan: Sequence[tuple[int, int]] = PLAN,
) -> ResultadoEscalabilidad:
    """Mide los tres algoritmos en cada tamaño del plan.

    >>> r = ejecutar_escalabilidad(((100, 2), (200, 2)))
    >>> len(r.filas), [g.nodos for g in r.grafos]
    (6, [100, 200])
    """
    medidas: list[FilaBenchmark] = []
    aristas: dict[int, int] = {}
    grafos = []
    for cantidad_nodos, consultas in plan:
        segundos, kilobytes, grafo = medir_tiempo_y_memoria(
            partial(generar_grafo, cantidad_nodos)
        )
        aristas[cantidad_nodos] = grafo.cantidad_aristas()
        grafos.append(
            MemoriaGrafo(
                cantidad_nodos,
                aristas[cantidad_nodos],
                kilobytes / KB_POR_MB,
                segundos / 1000,
            )
        )
        medidas.extend(medir_algoritmos(grafo, consultas))
    return ResultadoEscalabilidad(
        comparar_con_teoria(medidas, aristas), grafos
    )
