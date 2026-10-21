"""Ejecución secuencial vs hilos vs procesos de varias consultas."""

import time
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import NamedTuple

from rutas.algoritmos import dijkstra
from rutas.generador import Consulta, generar_consultas, generar_grafo
from rutas.grafo import Grafo
from rutas.mediciones import medir_tiempo_y_memoria

BYTES_POR_KB = 1024
TAMANO_LOTE = 10  # consultas que recibe cada proceso por tarea

# Grafo compartido por las funciones de trabajo. Cada proceso hijo recibe
# su propia copia mediante ``_iniciar_trabajador``. Es un global a propósito:
# los procesos del pool solo pueden compartir estado así.
_grafo_trabajo: Grafo | None = None  # pylint: disable=invalid-name


class FilaConcurrencia(NamedTuple):
    """Resultado de un modo de ejecución."""

    modo: str
    tiempo_ms: float
    memoria_kb: float
    consultas_procesadas: int
    aceleracion: float  # tiempo secuencial / tiempo del modo


def _grafo_activo() -> Grafo:
    """Devuelve el grafo del trabajador; falla si no se inicializó."""
    if _grafo_trabajo is None:
        raise RuntimeError("El grafo de trabajo no fue inicializado")
    return _grafo_trabajo


def _iniciar_trabajador(grafo: Grafo, medir_memoria: bool = False) -> None:
    """Inicializador de cada proceso: guarda el grafo y activa tracemalloc."""
    global _grafo_trabajo  # pylint: disable=global-statement
    _grafo_trabajo = grafo
    if medir_memoria:
        tracemalloc.start()


def _resolver(consulta: Consulta) -> float:
    """Resuelve una consulta con Dijkstra y devuelve la distancia."""
    return dijkstra(_grafo_activo(), *consulta).distancia


def _resolver_midiendo_memoria(consulta: Consulta) -> int:
    """Resuelve una consulta y devuelve el pico de memoria en bytes."""
    tracemalloc.reset_peak()
    dijkstra(_grafo_activo(), *consulta)
    return tracemalloc.get_traced_memory()[1]


def _ejecutar_procesos(
    grafo: Grafo,
    consultas: list[Consulta],
    trabajadores: int,
    medir_memoria: bool,
) -> list:
    """Reparte las consultas entre procesos y devuelve sus resultados."""
    funcion = _resolver_midiendo_memoria if medir_memoria else _resolver
    with ProcessPoolExecutor(
        trabajadores,
        initializer=_iniciar_trabajador,
        initargs=(grafo, medir_memoria),
    ) as ejecutor:
        return list(ejecutor.map(funcion, consultas, chunksize=TAMANO_LOTE))


def ejecutar_concurrencia(
    cantidad_nodos: int = 2000,
    cantidad_consultas: int = 300,
    trabajadores: int = 4,
) -> list[FilaConcurrencia]:
    """Compara los tres modos con las mismas consultas.

    El tiempo de los procesos incluye crear el pool y copiar el grafo.
    La memoria de los procesos es el mayor pico entre sus trabajadores.
    """
    global _grafo_trabajo  # pylint: disable=global-statement
    grafo = generar_grafo(cantidad_nodos, semilla=3)
    grafo.factor_heuristica()
    consultas = generar_consultas(grafo, cantidad_consultas, semilla=9)
    _grafo_trabajo = grafo

    def secuencial() -> list:
        return [_resolver(consulta) for consulta in consultas]

    def con_hilos() -> list:
        with ThreadPoolExecutor(trabajadores) as ejecutor:
            return list(ejecutor.map(_resolver, consultas))

    medidas: list[tuple[str, float, float, int]] = []
    for nombre, funcion in (
        ("Secuencial", secuencial),
        (f"Hilos ({trabajadores})", con_hilos),
    ):
        tiempo, memoria, resultados = medir_tiempo_y_memoria(funcion)
        medidas.append((nombre, tiempo, memoria, len(resultados)))

    inicio = time.perf_counter()
    resultados = _ejecutar_procesos(grafo, consultas, trabajadores, False)
    tiempo = (time.perf_counter() - inicio) * 1000
    picos = _ejecutar_procesos(grafo, consultas, trabajadores, True)
    medidas.append(
        (
            f"Procesos ({trabajadores})",
            tiempo,
            max(picos) / BYTES_POR_KB,
            len(resultados),
        )
    )

    base = medidas[0][1]
    return [FilaConcurrencia(*fila, base / fila[1]) for fila in medidas]
