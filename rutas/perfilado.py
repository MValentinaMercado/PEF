"""Perfilado real de los tres algoritmos.

cProfile (ver con SnakeViz) mide por función, line_profiler mide el tiempo de
cada línea y memory_profiler mide la memoria de cada línea.
"""

import cProfile
import io
import linecache
import os
import pstats
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple

import line_profiler
from memory_profiler import LineProfiler, show_results

from rutas.algoritmos import ALGORITMOS, Algoritmo, a_estrella, bfs, dijkstra
from rutas.algoritmos.comunes import buscar_con_heap
from rutas.generador import (
    Consulta,
    generar_consultas,
    generar_grafo,
    preparar_escenario,
)
from rutas.grafo import Grafo


class FilaPerfil(NamedTuple):
    """Costo de una función según cProfile."""

    funcion: str
    llamadas: int
    tiempo_propio: float  # excluye subfunciones
    tiempo_acumulado: float  # incluye subfunciones


def perfilar_algoritmo(
    algoritmo: Algoritmo,
    grafo: Grafo,
    consultas: Sequence[Consulta],
    cantidad: int = 6,
    guardar_en: Path | None = None,
) -> list[FilaPerfil]:
    """Perfila el algoritmo y devuelve las funciones de mayor tiempo propio.

    Si se indica ``guardar_en`` también se escribe el perfil completo en ese
    archivo ``.prof``, que es el formato que lee SnakeViz.
    """
    perfil = cProfile.Profile()
    perfil.enable()
    for origen, destino in consultas:
        algoritmo(grafo, origen, destino)
    perfil.disable()
    if guardar_en is not None:
        perfil.dump_stats(str(guardar_en))
    filas = []
    estadisticas = pstats.Stats(perfil)
    # ``stats`` existe en tiempo de ejecución pero typeshed no lo declara.
    for (archivo, _, nombre), datos in estadisticas.stats.items():  # type: ignore[attr-defined]
        _, llamadas, propio, acumulado, _ = datos
        etiqueta = (
            nombre
            if archivo == "~"
            else f"{os.path.basename(archivo)}:{nombre}"
        )
        filas.append(FilaPerfil(etiqueta, llamadas, propio, acumulado))
    filas.sort(key=lambda fila: fila.tiempo_propio, reverse=True)
    return filas[:cantidad]


def nombre_archivo_prof(nombre_algoritmo: str) -> str:
    """Nombre seguro de archivo ``.prof`` para un algoritmo.

    >>> nombre_archivo_prof("A*")
    'a_estrella.prof'
    >>> nombre_archivo_prof("Dijkstra")
    'dijkstra.prof'
    """
    seguro = nombre_algoritmo.lower().replace("*", "_estrella")
    return re.sub(r"[^a-z0-9_]", "_", seguro) + ".prof"


def ejecutar_perfilado(
    cantidad_nodos: int = 5000,
    cantidad_consultas: int = 20,
    carpeta_prof: Path | None = None,
) -> dict[str, list[FilaPerfil]]:
    """Perfila cada algoritmo sobre las mismas consultas.

    Con ``carpeta_prof`` deja un ``.prof`` por algoritmo para abrirlo en
    SnakeViz.
    """
    grafo, consultas = preparar_escenario(cantidad_nodos, cantidad_consultas)
    if carpeta_prof is not None:
        carpeta_prof.mkdir(parents=True, exist_ok=True)
    return {
        nombre: perfilar_algoritmo(
            algoritmo,
            grafo,
            consultas,
            guardar_en=(
                carpeta_prof / nombre_archivo_prof(nombre)
                if carpeta_prof
                else None
            ),
        )
        for nombre, algoritmo in ALGORITMOS.items()
    }


class FilaLinea(NamedTuple):
    """Una línea de un algoritmo según line_profiler."""

    linea: int
    ejecuciones: int
    tiempo_us: float
    porcentaje: float  # del tiempo total medido dentro de la función
    codigo: str


# Función cuyas líneas se miden en cada algoritmo. Dijkstra y A* comparten el
# bucle (``buscar_con_heap``): ``dijkstra`` y ``a_estrella`` solo lo invocan.
FUNCION_PERFILADA = {
    "BFS": bfs,
    "Dijkstra": buscar_con_heap,
    "A*": buscar_con_heap,
}


def perfilar_lineas(
    algoritmo: Algoritmo,
    grafo: Grafo,
    consultas: Sequence[Consulta],
    funcion: Callable | None = None,
) -> list[FilaLinea]:
    """Tiempo de cada línea de ``funcion`` mientras corre ``algoritmo``.

    ``funcion`` es la que se mide (por defecto, el propio algoritmo). Se usa
    ``line_profiler``.

    El perfilador agrega un costo fijo por línea ejecutada: sirve para
    comparar líneas entre sí (porcentajes), no para medir tiempos absolutos.
    """
    perfilador = line_profiler.LineProfiler()
    perfilador.add_function(funcion or algoritmo)
    perfilador.enable_by_count()
    for origen, destino in consultas:
        algoritmo(grafo, origen, destino)
    perfilador.disable_by_count()
    estadisticas = perfilador.get_stats()
    filas: list[FilaLinea] = []
    for (archivo, _, _), lineas in estadisticas.timings.items():
        total = sum(tiempo for _, _, tiempo in lineas) or 1
        filas.extend(
            FilaLinea(
                numero,
                ejecuciones,
                tiempo * estadisticas.unit * 1e6,
                100 * tiempo / total,
                linecache.getline(archivo, numero).strip(),
            )
            for numero, ejecuciones, tiempo in lineas
        )
    return filas


def ejecutar_perfilado_lineas(
    cantidad_nodos: int = 5000,
    cantidad_consultas: int = 20,
) -> dict[str, list[FilaLinea]]:
    """Perfila línea por línea cada algoritmo sobre las mismas consultas.

    >>> filas = ejecutar_perfilado_lineas(200, 2)["Dijkstra"]
    >>> any("heappop" in fila.codigo for fila in filas)
    True
    >>> round(sum(fila.porcentaje for fila in filas))
    100
    """
    grafo, consultas = preparar_escenario(cantidad_nodos, cantidad_consultas)
    return {
        nombre: perfilar_lineas(
            algoritmo, grafo, consultas, FUNCION_PERFILADA[nombre]
        )
        for nombre, algoritmo in ALGORITMOS.items()
    }


class FilaMemoria(NamedTuple):
    """Una línea de código según memory_profiler."""

    linea: int
    memoria_mib: float
    incremento_mib: float
    codigo: str


_LINEA_MEMORIA = re.compile(
    r"^\s*+(\d++)\s++([\d.]++) MiB\s++(-?[\d.]++) MiB\s++\d++\s++(.*)$"
)


def _consultas_de_memoria(cantidad_nodos: int) -> None:
    """Función perfilada: cada paso en su propia línea para medirlo."""
    grafo = generar_grafo(cantidad_nodos, semilla=7)
    grafo.factor_heuristica()
    origen, destino = generar_consultas(grafo, 1, semilla=4)[0]
    bfs(grafo, origen, destino)
    dijkstra(grafo, origen, destino)
    a_estrella(grafo, origen, destino)


def ejecutar_perfilado_memoria(
    cantidad_nodos: int = 5000,
) -> list[FilaMemoria]:
    """Memoria línea por línea con ``memory_profiler``.

    >>> filas = ejecutar_perfilado_memoria(200)
    >>> any("generar_grafo" in fila.codigo for fila in filas)
    True
    """
    perfilador = LineProfiler(backend="psutil")
    funcion = perfilador(_consultas_de_memoria)
    funcion(cantidad_nodos)
    salida = io.StringIO()
    show_results(perfilador, stream=salida)
    filas = []
    for texto in salida.getvalue().splitlines():
        coincidencia = _LINEA_MEMORIA.match(texto)
        if coincidencia:
            linea, memoria, incremento, codigo = coincidencia.groups()
            filas.append(
                FilaMemoria(
                    int(linea),
                    float(memoria),
                    float(incremento),
                    codigo.strip(),
                )
            )
    return filas
