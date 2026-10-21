"""Endpoints de la ventana Análisis.

Incluye benchmark, escalabilidad, caché, concurrencia, entrada/salida,
perfilado (cProfile, SnakeViz, line_profiler, memory_profiler y Scalene) y
predicción de tiempos con IA.

Cada medición es costosa, por eso los endpoints son ``def`` normales:
FastAPI los ejecuta en un pool de hilos y no bloquea el servidor.
"""

from fastapi import APIRouter, HTTPException, Query

from api import visor_perfiles
from api.estado import estado
from rutas.algoritmos import ALGORITMOS
from rutas.benchmark import ejecutar_benchmark
from rutas.concurrencia import ejecutar_concurrencia
from rutas.entrada_salida import ejecutar_entrada_salida
from rutas.escalabilidad import ejecutar_escalabilidad
from rutas.experimento_cache import ejecutar_experimento_cache
from rutas.perfilado import (
    ejecutar_perfilado,
    ejecutar_perfilado_lineas,
    ejecutar_perfilado_memoria,
    nombre_archivo_prof,
)
from rutas.perfilado_scalene import ejecutar_scalene
from rutas.prediccion import advertencias, entrenar_y_evaluar

router = APIRouter(prefix="/api/analisis")


@router.post("/benchmark")
def benchmark() -> list:
    """BFS, Dijkstra y A* con grafos de 100, 1.000 y 5.000 nodos."""
    with estado.cerrojo_medicion:
        return [fila._asdict() for fila in ejecutar_benchmark()]


@router.post("/escalabilidad")
def escalabilidad() -> dict:
    """Hasta 100.000 nodos: tiempo y memoria frente a la teoría.

    Tarda unos 25 segundos, por eso la página lo ejecuta solo a pedido.
    """
    with estado.cerrojo_medicion:
        resultado = ejecutar_escalabilidad()
    return {
        "filas": [fila._asdict() for fila in resultado.filas],
        "grafos": [grafo._asdict() for grafo in resultado.grafos],
    }


@router.post("/prediccion")
def prediccion() -> dict:
    """Mide, entrena y evalúa la regresión que predice tiempos.

    Deja el modelo entrenado en memoria para ``/prediccion/recomendar``.
    Tarda unos segundos: son mediciones reales sobre 40 grafos.
    """
    with estado.cerrojo_medicion:
        resultado = entrenar_y_evaluar()
    estado.modelo = resultado.modelo
    return {
        "entrenamiento": resultado.entrenamiento,
        "evaluaciones": [e._asdict() for e in resultado.evaluaciones],
        "pruebas": [fila._asdict() for fila in resultado.pruebas],
        "seleccion": resultado.seleccion._asdict(),
    }


@router.get("/prediccion/recomendar")
def recomendar(
    nodos: int = Query(ge=2, le=10_000_000),
    aristas: int = Query(ge=1, le=100_000_000),
    ponderado: bool = True,
) -> dict:
    """Tiempo predicho y algoritmo recomendado para un grafo no medido."""
    if estado.modelo is None:
        raise HTTPException(409, "Primero entrená el modelo.")
    return estado.modelo.recomendar(nodos, aristas, ponderado)._asdict() | {
        "advertencias": advertencias(nodos, aristas)
    }


@router.post("/cache")
def cache() -> dict:
    """Consultas con y sin caché."""
    with estado.cerrojo_medicion:
        return ejecutar_experimento_cache()._asdict()


@router.post("/concurrencia")
def concurrencia() -> list:
    """Secuencial vs hilos vs procesos."""
    with estado.cerrojo_medicion:
        return [fila._asdict() for fila in ejecutar_concurrencia()]


@router.post("/entrada_salida")
def entrada_salida() -> dict:
    """Archivo grande: buffer al escribir, lotes al leer y paralelismo."""
    with estado.cerrojo_medicion:
        resultado = ejecutar_entrada_salida()
    datos = resultado._asdict()
    for tabla in ("escritura", "lectura", "paralelo"):
        datos[tabla] = [fila._asdict() for fila in datos[tabla]]
    return datos


@router.post("/perfilado")
def perfilado() -> dict:
    """cProfile por algoritmo y memory_profiler línea por línea.

    Además deja un ``.prof`` por algoritmo para verlo con SnakeViz.
    """
    with estado.cerrojo_medicion:
        cpu = {
            nombre: [fila._asdict() for fila in filas]
            for nombre, filas in ejecutar_perfilado(
                carpeta_prof=visor_perfiles.CARPETA_PERFILES
            ).items()
        }
        memoria = [fila._asdict() for fila in ejecutar_perfilado_memoria()]
        return {"cpu": cpu, "memoria": memoria}


@router.post("/lineas")
def lineas() -> dict:
    """line_profiler: tiempo de cada línea de BFS, Dijkstra y A*."""
    with estado.cerrojo_medicion:
        return {
            nombre: [fila._asdict() for fila in filas]
            for nombre, filas in ejecutar_perfilado_lineas().items()
        }


@router.post("/scalene")
def scalene() -> dict:
    """Scalene: CPU (Python, nativo, sistema) y memoria por línea."""
    with estado.cerrojo_medicion:
        try:
            resultado = ejecutar_scalene()
        except RuntimeError as error:
            raise HTTPException(500, str(error)) from error
    return resultado._asdict() | {
        "filas": [fila._asdict() for fila in resultado.filas]
    }


@router.post("/snakeviz")
def snakeviz() -> dict:
    """Levanta SnakeViz y devuelve la dirección del perfil de cada algoritmo.

    Hay que ejecutar antes el perfilado para que existan los ``.prof``.
    """
    perfiles = {
        nombre: visor_perfiles.CARPETA_PERFILES / nombre_archivo_prof(nombre)
        for nombre in ALGORITMOS
    }
    if not all(archivo.exists() for archivo in perfiles.values()):
        raise HTTPException(409, "Primero ejecutá el perfilado de CPU.")
    try:
        visor_perfiles.iniciar(next(iter(perfiles.values())))
    except RuntimeError as error:
        raise HTTPException(500, str(error)) from error
    return {
        nombre: visor_perfiles.url_perfil(a) for nombre, a in perfiles.items()
    }
