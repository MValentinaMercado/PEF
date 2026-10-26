"""Perfilado real de los tres algoritmos.

cProfile (ver con SnakeViz) mide por función, line_profiler mide el tiempo de
cada línea y memory_profiler mide la memoria de cada línea.
"""

import cProfile
import linecache
import os
import pstats
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple

import line_profiler
from memory_profiler import LineProfiler

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
    tiempo_propio: float  # Excluye subfunciones.
    tiempo_acumulado: float  # Incluye subfunciones.


def perfilar_algoritmo(
    algoritmo: Algoritmo,
    grafo: Grafo,
    consultas: Sequence[Consulta],
    cantidad: int = 6,
    guardar_en: Path | None = None,
) -> list[FilaPerfil]:
    """Perfila el algoritmo y devuelve las funciones de mayor tiempo propio.

    Si se indica ``guardar_en``, también se escribe el perfil completo en ese
    archivo ``.prof``, que es el formato que lee SnakeViz.
    """
    perfil = cProfile.Profile()
    perfil.enable()

    for origen, destino in consultas:
        algoritmo(grafo, origen, destino)

    perfil.disable()

    if guardar_en is not None:
        guardar_en.parent.mkdir(parents=True, exist_ok=True)
        perfil.dump_stats(str(guardar_en))

    filas: list[FilaPerfil] = []
    estadisticas = pstats.Stats(perfil)

    # ``stats`` existe en tiempo de ejecución, aunque typeshed no lo declara.
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
    """Devuelve un nombre seguro de archivo ``.prof``.

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

    Con ``carpeta_prof`` deja un archivo ``.prof`` por algoritmo para abrirlo
    en SnakeViz.
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
                if carpeta_prof is not None
                else None
            ),
        )
        for nombre, algoritmo in ALGORITMOS.items()
    }


class FilaLinea(NamedTuple):
    """Una línea de código según line_profiler."""

    linea: int
    ejecuciones: int
    tiempo_us: float
    porcentaje: float  # Porcentaje del tiempo total medido en la función.
    codigo: str


# BFS se mide directamente. Dijkstra y A* comparten el bucle de heap.
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
    """Mide el tiempo de cada línea de ``funcion`` mientras corre ``algoritmo``.

    ``funcion`` es la función que se mide; si se omite, se mide el algoritmo.
    Se utiliza ``line_profiler``.

    El perfilador agrega un costo fijo por línea ejecutada: sirve para comparar
    líneas entre sí mediante porcentajes, no para medir tiempos absolutos.
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
            algoritmo,
            grafo,
            consultas,
            FUNCION_PERFILADA[nombre],
        )
        for nombre, algoritmo in ALGORITMOS.items()
    }


class FilaMemoria(NamedTuple):
    """Una línea de código según memory_profiler."""

    linea: int
    memoria_mib: float
    incremento_mib: float
    codigo: str


# Acepta espacios variables y números enteros o decimales en la salida
# de memory_profiler. El código fuente queda capturado al final de la línea.
_LINEA_MEMORIA = re.compile(
    r"^\s*\*+\s*(\d+)\s+([\d.]+)\s+MiB\s+"
    r"(-?[\d.]+)\s+MiB\s+\d+\s+(.*?)\s*$"
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
    """Mide la memoria línea por línea con ``memory_profiler``.

    >>> filas = ejecutar_perfilado_memoria(200)
    >>> any("generar_grafo" in fila.codigo for fila in filas)
    True
    """
    perfilador = LineProfiler(backend="psutil")
    perfilador(_consultas_de_memoria)(cantidad_nodos)

    codigo = _consultas_de_memoria.__code__
    archivo = codigo.co_filename
    datos_funcion = perfilador.code_map.get(codigo, {})

    filas: list[FilaMemoria] = []

    for numero, mediciones in sorted(datos_funcion.items()):
        memoria_mib, incremento_acumulado_mib, _ = mediciones
        texto_codigo = linecache.getline(archivo, numero).strip()

        filas.append(
            FilaMemoria(
                linea=int(numero),
                memoria_mib=float(memoria_mib),
                incremento_mib=float(incremento_acumulado_mib),
                codigo=texto_codigo,
            )
        )

    return filas
