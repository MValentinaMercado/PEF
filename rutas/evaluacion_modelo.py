"""Costo y utilidad del modelo de IA frente a la solución convencional.

La regresión de ``rutas.prediccion`` (scikit-learn) estima cuánto tarda un
algoritmo en un grafo que todavía no se midió. Que funcione no alcanza: hay
que demostrar **cuánto cuesta** y **cuándo conviene** frente a lo más simple,
que es ejecutar el algoritmo y medir. Este módulo hace cuatro mediciones
independientes:

* **Entrenamiento**: tiempo de reunir los datos, tiempo de ajustar los
  regresores, memoria pico y tamaño del modelo.
* **Precisión**: error absoluto (MAE, en ms) y porcentual (MAPE) sobre grafos
  que no se usaron al entrenar, contra una referencia sin IA (predecir
  siempre el tiempo medio del entrenamiento).
* **Latencia**: cuánto tarda y cuánta memoria usa una predicción.
* **Comparación**: predecir contra ejecutar el algoritmo, y cuántas
  estimaciones hacen falta para recuperar el costo de entrenar.

Las conclusiones se redactan con reglas fijas y umbrales explícitos (las
constantes ``UMBRAL_*``) sobre los números medidos: no interviene ninguna IA
y el mismo resultado produce siempre el mismo texto. Los tiempos son la
**mediana** de varias repeticiones, porque una sola medición varía con la
carga de la máquina.
"""

import pickle
import statistics
import time
import tracemalloc
from collections.abc import Callable, Sequence
from functools import partial
from typing import NamedTuple

from rutas.algoritmos import ALGORITMOS
from rutas.generador import generar_consultas, generar_grafo
from rutas.mediciones import BYTES_POR_KB
from rutas.prediccion import (
    PLAN_ENTRENAMIENTO,
    PLAN_PRUEBA,
    ModeloTiempos,
    Muestra,
    medir_muestras,
)

# Criterios del equipo (se documentan en documentacion/ia.md).
UMBRAL_ERROR_BUENO_PCT = 10.0  # error medio que permite estimar con confianza
UMBRAL_ERROR_ACEPTABLE_PCT = 25.0  # solo sirve para el orden de magnitud
UMBRAL_LATENCIA_BAJA_US = 1000.0  # una predicción por debajo de 1 ms
UMBRAL_AMORTIZACION = 1000  # estimaciones razonables para recuperar el costo

REPETICIONES_AJUSTE = 5
REPETICIONES_PREDICCION = 2000
BLOQUES_PREDICCION = 5
CONSULTAS_COMPARACION = 3
ALGORITMO_COMPARADO = "Dijkstra"
# Ninguno coincide con el plan de entrenamiento ni con el de prueba.
PLAN_COMPARACION = ((100, 3), (1_500, 4), (15_000, 4), (40_000, 4))
SEMILLA_COMPARACION = 11


class CostoEntrenamiento(NamedTuple):
    """Lo que cuesta construir el modelo."""

    muestras: int
    recoleccion_s: float  # medir los grafos de entrenamiento
    ajuste_ms: float  # solo ``fit`` de scikit-learn (mediana)
    memoria_ajuste_kb: float  # pico de ``tracemalloc`` durante el ajuste
    tamano_modelo_bytes: int


class Entrenado(NamedTuple):
    """Modelo entrenado, sus datos y lo que costó."""

    modelo: ModeloTiempos
    entrenamiento: list[Muestra]
    prueba: list[Muestra]
    costo: CostoEntrenamiento


class FilaPrecision(NamedTuple):
    """Error del modelo y de la referencia sin IA en un algoritmo."""

    algoritmo: str
    grafos: int
    mae_ms: float
    error_medio_pct: float
    mae_referencia_ms: float
    error_referencia_pct: float


class Latencia(NamedTuple):
    """Costo de una predicción."""

    repeticiones: int
    prediccion_us: float
    recomendacion_us: float
    memoria_kb: float


class FilaComparacion(NamedTuple):
    """Predecir contra ejecutar el algoritmo en un grafo no visto."""

    nodos: int
    aristas: int
    directo_ms: float
    predicho_ms: float
    error_pct: float
    prediccion_us: float
    veces_mas_rapida: float  # ejecutar / predecir; menor que 1: pierde


class Comparacion(NamedTuple):
    """Filas por tamaño y cuánto tarda en amortizarse el entrenamiento."""

    algoritmo: str
    filas: list[FilaComparacion]
    costo_entrenamiento_ms: float
    estimaciones_para_amortizar: int | None  # None: nunca se amortiza


def _numero(valor: float, decimales: int = 1) -> str:
    """Número con el formato del resto de la aplicación (1.234,5).

    >>> _numero(1234.567)
    '1.234,6'
    >>> _numero(0.5, 2)
    '0,50'
    """
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _porcentaje_error(predicho: float, medido: float) -> float:
    """Error relativo en porcentaje."""
    return 100 * abs(predicho - medido) / medido


# --- entrenamiento ---
def medir_entrenamiento(
    plan_entrenamiento: Sequence[tuple[int, int]] = PLAN_ENTRENAMIENTO,
    plan_prueba: Sequence[tuple[int, int]] = PLAN_PRUEBA,
) -> Entrenado:
    """Mide los datos, entrena y registra cuánto costó cada parte.

    El tiempo de ajuste es la mediana de varias repeticiones y la memoria se
    toma en otra corrida con ``tracemalloc``, que enlentece y falsearía el
    tiempo (el mismo criterio que ``rutas.mediciones``).

    >>> e = medir_entrenamiento(((100, 2), (200, 3), (400, 4)), ((300, 3),))
    >>> e.costo.muestras, e.costo.tamano_modelo_bytes > 0
    (9, True)
    """
    inicio = time.perf_counter()
    entrenamiento = medir_muestras(plan_entrenamiento)
    recoleccion_s = time.perf_counter() - inicio
    prueba = medir_muestras(plan_prueba)
    tiempos = []
    for _ in range(REPETICIONES_AJUSTE):
        inicio = time.perf_counter()
        modelo = ModeloTiempos().entrenar(entrenamiento)
        tiempos.append(1000 * (time.perf_counter() - inicio))
    tracemalloc.start()
    ModeloTiempos().entrenar(entrenamiento)
    pico = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    costo = CostoEntrenamiento(
        len(entrenamiento),
        recoleccion_s,
        statistics.median(tiempos),
        pico / BYTES_POR_KB,
        len(pickle.dumps(modelo.regresores)),
    )
    return Entrenado(modelo, entrenamiento, prueba, costo)


def concluir_entrenamiento(costo: CostoEntrenamiento) -> str:
    """Conclusión sobre el costo de entrenar, por reglas fijas.

    >>> c = CostoEntrenamiento(60, 3.0, 6.0, 90.0, 2300)
    >>> "99,8 %" in concluir_entrenamiento(c)
    True
    """
    total_ms = costo.recoleccion_s * 1000 + costo.ajuste_ms
    parte_datos = 100 * costo.recoleccion_s * 1000 / total_ms
    texto = (
        f"Entrenar costó {_numero(total_ms / 1000, 1)} s en total: "
        f"{_numero(costo.recoleccion_s, 1)} s para medir {costo.muestras} "
        f"muestras reales y {_numero(costo.ajuste_ms, 1)} ms para ajustar "
        f"los regresores (mediana de {REPETICIONES_AJUSTE} repeticiones), "
        f"con un pico de {_numero(costo.memoria_ajuste_kb, 0)} KB. El modelo "
        f"pesa {_numero(costo.tamano_modelo_bytes / BYTES_POR_KB, 1)} KB. "
    )
    if parte_datos >= 90:
        return texto + (
            f"El {_numero(parte_datos, 1)} % del costo es obtener los datos, "
            "no el aprendizaje: ajustar un modelo lineal es casi gratis, lo "
            "caro es medir los grafos de ejemplo."
        )
    return texto + (
        f"Obtener los datos representa el {_numero(parte_datos, 1)} % del "
        "costo; el ajuste del modelo pesa más de lo esperado."
    )


# --- precisión ---
def _fila_precision(entrenado: Entrenado, algoritmo: str) -> FilaPrecision:
    """Error del modelo y de la referencia sin IA en un algoritmo."""
    medios = statistics.fmean(
        m.tiempo_ms
        for m in entrenado.entrenamiento
        if m.algoritmo == algoritmo
    )
    nuevas = [m for m in entrenado.prueba if m.algoritmo == algoritmo]
    predichos = [
        entrenado.modelo.predecir(algoritmo, m.nodos, m.aristas)
        for m in nuevas
    ]
    return FilaPrecision(
        algoritmo,
        len(nuevas),
        statistics.fmean(
            abs(p - m.tiempo_ms)
            for p, m in zip(predichos, nuevas, strict=True)
        ),
        statistics.fmean(
            _porcentaje_error(p, m.tiempo_ms)
            for p, m in zip(predichos, nuevas, strict=True)
        ),
        statistics.fmean(abs(medios - m.tiempo_ms) for m in nuevas),
        statistics.fmean(
            _porcentaje_error(medios, m.tiempo_ms) for m in nuevas
        ),
    )


def medir_precision(entrenado: Entrenado) -> list[FilaPrecision]:
    """Error en grafos no vistos, contra predecir siempre el tiempo medio.

    >>> muestras = [Muestra(n, 3 * n, "BFS", 0.01 * n) for n in (10, 20, 40)]
    >>> modelo = ModeloTiempos().entrenar(muestras)
    >>> prueba = [Muestra(80, 240, "BFS", 0.8)]
    >>> costo = CostoEntrenamiento(3, 1, 1, 1, 1)
    >>> e = Entrenado(modelo, muestras, prueba, costo)
    >>> medir_precision(e)[0].error_medio_pct < 1e-6
    True
    """
    return [
        _fila_precision(entrenado, algoritmo)
        for algoritmo in sorted({m.algoritmo for m in entrenado.prueba})
    ]


def concluir_precision(filas: Sequence[FilaPrecision]) -> str:
    """Conclusión sobre la precisión, con umbrales explícitos.

    >>> f = [FilaPrecision("BFS", 5, 0.2, 8.0, 3.0, 90.0)]
    >>> "es buena" in concluir_precision(f)
    True
    >>> f = [FilaPrecision("BFS", 5, 2.0, 40.0, 3.0, 30.0)]
    >>> "no mejora" in concluir_precision(f)
    True
    """
    error = statistics.fmean(f.error_medio_pct for f in filas)
    mae = statistics.fmean(f.mae_ms for f in filas)
    mejoran = sum(f.error_medio_pct < f.error_referencia_pct for f in filas)
    texto = (
        f"En {filas[0].grafos} grafos que el modelo no vio, el error absoluto "
        f"medio (MAE) fue de {_numero(mae, 2)} ms y el error porcentual medio "
        f"de {_numero(error, 1)} %. Frente a predecir siempre el tiempo medio "
        f"del entrenamiento, el modelo fue mejor en {mejoran} de "
        f"{len(filas)} algoritmos. "
    )
    if error <= UMBRAL_ERROR_BUENO_PCT:
        veredicto = (
            "El error está por debajo del "
            f"{_numero(UMBRAL_ERROR_BUENO_PCT, 0)} %: la precisión es buena "
            "para estimar tiempos."
        )
    elif error <= UMBRAL_ERROR_ACEPTABLE_PCT:
        veredicto = (
            "La precisión es aceptable para ubicar el orden de magnitud, pero "
            "no para distinguir diferencias pequeñas entre algoritmos."
        )
    else:
        veredicto = (
            f"El error supera el {_numero(UMBRAL_ERROR_ACEPTABLE_PCT, 0)} %: "
            "la precisión es insuficiente y conviene medir directamente."
        )
    if mejoran < len(filas):
        veredicto += " En algún algoritmo el modelo no mejora la referencia."
    return texto + veredicto


# --- latencia ---
def _mediana_por_llamada_us(
    llamada: Callable[[], object], repeticiones: int
) -> float:
    """Microsegundos por llamada: mediana de varios bloques de llamadas."""
    por_bloque = repeticiones // BLOQUES_PREDICCION
    medianas = []
    for _ in range(BLOQUES_PREDICCION):
        inicio = time.perf_counter()
        for _ in range(por_bloque):
            llamada()
        medianas.append(1e6 * (time.perf_counter() - inicio) / por_bloque)
    return statistics.median(medianas)


def medir_latencia(
    modelo: ModeloTiempos, repeticiones: int = REPETICIONES_PREDICCION
) -> Latencia:
    """Tiempo y memoria de una predicción y de una recomendación.

    >>> m = ModeloTiempos().entrenar(
    ...     [Muestra(n, 3 * n, a, 0.01 * n) for n in (10, 20, 40)
    ...      for a in ("BFS", "Dijkstra", "A*")]
    ... )
    >>> medir_latencia(m, 50).prediccion_us > 0
    True
    """
    prediccion = _mediana_por_llamada_us(
        lambda: modelo.predecir(ALGORITMO_COMPARADO, 10_000, 30_000),
        repeticiones,
    )
    recomendacion = _mediana_por_llamada_us(
        lambda: modelo.recomendar(10_000, 30_000), repeticiones
    )
    tracemalloc.start()
    modelo.recomendar(10_000, 30_000)
    pico = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return Latencia(
        repeticiones, prediccion, recomendacion, pico / BYTES_POR_KB
    )


def concluir_latencia(latencia: Latencia) -> str:
    """Conclusión sobre el costo de consultar el modelo.

    >>> "despreciable" in concluir_latencia(Latencia(2000, 80.0, 250.0, 12.0))
    True
    >>> "alto" in concluir_latencia(Latencia(2000, 4000.0, 9000.0, 12.0))
    True
    """
    texto = (
        f"Una predicción tarda {_numero(latencia.prediccion_us, 0)} µs y una "
        f"recomendación entre los tres algoritmos "
        f"{_numero(latencia.recomendacion_us, 0)} µs (mediana de "
        f"{BLOQUES_PREDICCION} bloques de "
        f"{latencia.repeticiones // BLOQUES_PREDICCION} llamadas), con un "
        f"pico de {_numero(latencia.memoria_kb, 1)} KB por recomendación. "
    )
    if latencia.recomendacion_us < UMBRAL_LATENCIA_BAJA_US:
        return texto + (
            "El costo por consulta es despreciable (menos de 1 ms y de "
            "memoria insignificante): el problema de usar el modelo no es lo "
            "que cuesta consultarlo."
        )
    return texto + (
        "El costo por consulta es alto (1 ms o más): puede superar al de "
        "ejecutar el algoritmo en grafos chicos."
    )


# --- comparación ---
def comparar_con_medicion_directa(
    entrenado: Entrenado,
    plan: Sequence[tuple[int, int]] = PLAN_COMPARACION,
    consultas: int = CONSULTAS_COMPARACION,
) -> Comparacion:
    """Predecir contra ejecutar el algoritmo, en grafos nunca vistos.

    La alternativa convencional es ejecutar el algoritmo y medir cuánto
    tarda. Además calcula cuántas estimaciones hacen falta para que el ahorro
    por consulta compense el costo de entrenar (en el grafo más grande).

    >>> muestras = [Muestra(n, 3 * n, "Dijkstra", 0.01 * n) for n in (50, 100)]
    >>> modelo = ModeloTiempos().entrenar(muestras)
    >>> e = Entrenado(modelo, muestras, [], CostoEntrenamiento(2, 1, 1, 1, 1))
    >>> r = comparar_con_medicion_directa(e, ((60, 3),), consultas=1)
    >>> r.algoritmo, len(r.filas)
    ('Dijkstra', 1)
    """
    algoritmo = ALGORITMOS[ALGORITMO_COMPARADO]
    filas = []
    for nodos, vecinos in plan:
        grafo = generar_grafo(
            nodos, semilla=SEMILLA_COMPARACION, vecinos_por_nodo=vecinos
        )
        grafo.factor_heuristica()
        tiempos = []
        for origen, destino in generar_consultas(grafo, consultas, semilla=5):
            inicio = time.perf_counter()
            algoritmo(grafo, origen, destino)
            tiempos.append(1000 * (time.perf_counter() - inicio))
        aristas = grafo.cantidad_aristas()
        directo = statistics.median(tiempos)
        predicho = entrenado.modelo.predecir(
            ALGORITMO_COMPARADO, nodos, aristas
        )
        prediccion_us = _mediana_por_llamada_us(
            partial(
                entrenado.modelo.predecir, ALGORITMO_COMPARADO, nodos, aristas
            ),
            200,
        )
        filas.append(
            FilaComparacion(
                nodos,
                aristas,
                directo,
                predicho,
                _porcentaje_error(predicho, directo),
                prediccion_us,
                directo * 1000 / prediccion_us,
            )
        )
    costo_ms = entrenado.costo.recoleccion_s * 1000 + entrenado.costo.ajuste_ms
    ahorro_ms = filas[-1].directo_ms - filas[-1].prediccion_us / 1000
    amortiza = int(costo_ms / ahorro_ms) + 1 if ahorro_ms > 0 else None
    return Comparacion(ALGORITMO_COMPARADO, filas, costo_ms, amortiza)


def _veredicto_comparacion(error: float, amortiza: int | None) -> str:
    """Veredicto según el error y las estimaciones para amortizar."""
    if error > UMBRAL_ERROR_ACEPTABLE_PCT:
        return (
            "Veredicto: conviene medir directamente: el error supera el "
            f"{_numero(UMBRAL_ERROR_ACEPTABLE_PCT, 0)} % aceptable."
        )
    if amortiza is None or amortiza > UMBRAL_AMORTIZACION:
        return (
            "Veredicto: conviene la solución convencional (ejecutar y "
            "medir): no se recupera el costo de entrenar con menos de "
            f"{_numero(UMBRAL_AMORTIZACION, 0)} estimaciones."
        )
    return (
        f"Veredicto: la IA se justifica solo si hacen falta más de "
        f"{_numero(amortiza, 0)} estimaciones de grafos grandes y se tolera "
        "ese error; para un grafo chico o una sola consulta, medir "
        "directamente es más simple y exacto, y no exige entrenar nada."
    )


def concluir_comparacion(comparacion: Comparacion) -> str:
    """Cuándo conviene la IA y cuándo la solución convencional.

    >>> fila = FilaComparacion(40000, 150000, 90.0, 80.0, 11.0, 60.0, 1500.0)
    >>> c = Comparacion("Dijkstra", [fila], 12000.0, 135)
    >>> "se justifica" in concluir_comparacion(c)
    True
    >>> malo = fila._replace(error_pct=60.0)
    >>> c = Comparacion("Dijkstra", [malo], 12000.0, 135)
    >>> "conviene medir" in concluir_comparacion(c)
    True
    """
    filas = comparacion.filas
    error = statistics.fmean(f.error_pct for f in filas)
    pierden = [f.nodos for f in filas if f.veces_mas_rapida < 1]
    texto = (
        f"Con grafos de {_numero(filas[0].nodos, 0)} a "
        f"{_numero(filas[-1].nodos, 0)} nodos, ejecutar "
        f"{comparacion.algoritmo} tardó de {_numero(filas[0].directo_ms, 3)} "
        f"a {_numero(filas[-1].directo_ms, 1)} ms, mientras que predecirlo "
        f"tarda entre {_numero(min(f.prediccion_us for f in filas), 0)} y "
        f"{_numero(max(f.prediccion_us for f in filas), 0)} µs, con un error "
        f"medio de {_numero(error, 1)} %. "
    )
    if pierden:
        texto += (
            "En los grafos de "
            + ", ".join(_numero(n, 0) for n in pierden)
            + " nodos ejecutar el algoritmo es más rápido que consultar el "
            "modelo. "
        )
    texto += (
        "Entrenar costó "
        f"{_numero(comparacion.costo_entrenamiento_ms / 1000, 1)} s. "
    )
    return texto + _veredicto_comparacion(
        error, comparacion.estimaciones_para_amortizar
    )
