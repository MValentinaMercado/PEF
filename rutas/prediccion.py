"""Componente de IA: regresión que predice cuánto tarda cada algoritmo.

Es aprendizaje supervisado de tipo **regresión** (predecir un número, como en
"Usar IA para detectar cuellos de botella"): a partir de la cantidad de nodos
y de aristas de un grafo, predice el tiempo de una consulta con BFS, Dijkstra
o A*. Con esa predicción se puede anticipar el costo de un grafo que todavía
no se midió y recomendar el algoritmo más rápido.

* **Datos**: tiempos reales medidos sobre grafos de distinto tamaño y
  densidad (no hay datos externos ni servicios de terceros).
* **Modelo**: ``LinearRegression`` de scikit-learn, el mismo ``lr`` que usa
  PyCaret, sobre logaritmos: ``ln(t) = a + b·ln(V) + c·ln(E)``. Equivale a
  ``t = e^a · V^b · E^c``, y los exponentes ``b`` y ``c`` se comparan con la
  complejidad teórica. Un modelo lineal directo no serviría: el tiempo no
  crece en línea recta con el tamaño.
* **Evaluación**: se prueba con grafos de tamaños que el modelo no vio.
"""

import math
import time
from collections.abc import Sequence
from typing import NamedTuple

from sklearn.linear_model import LinearRegression

from rutas.algoritmos import ALGORITMOS
from rutas.generador import generar_consultas, generar_grafo

# (cantidad de nodos, vecinos por nodo): el segundo número cambia la
# densidad, así el modelo ve más que grafos de un único tipo.
PLAN_ENTRENAMIENTO = tuple(
    (nodos, vecinos)
    for nodos in (500, 1_000, 2_000, 5_000, 10_000)
    for vecinos in (2, 3, 5, 8)
)
# Tamaños intermedios y mayores que todo lo visto al entrenar.
PLAN_PRUEBA = ((3_000, 4), (7_000, 2), (7_000, 5), (20_000, 3), (20_000, 6))
CONSULTAS = 8
DENSIDAD_ENTRENADA = (
    min(vecinos for _, vecinos in PLAN_ENTRENAMIENTO),
    max(vecinos for _, vecinos in PLAN_ENTRENAMIENTO),
)
NODOS_ENTRENADOS = max(nodos for nodos, _ in PLAN_ENTRENAMIENTO)
REGLA_FIJA = "Dijkstra"  # la alternativa sin IA contra la que se compara
# BFS minimiza saltos, no costo: en un grafo con pesos no es correcto.
CORRECTOS = {True: ("Dijkstra", "A*"), False: ("BFS", "Dijkstra", "A*")}


class Muestra(NamedTuple):
    """Tiempo medido de un algoritmo sobre un grafo."""

    nodos: int
    aristas: int
    algoritmo: str
    tiempo_ms: float


class FilaPrueba(NamedTuple):
    """Una predicción comparada con lo medido."""

    nodos: int
    aristas: int
    algoritmo: str
    medido_ms: float
    predicho_ms: float
    error_pct: float


class Evaluacion(NamedTuple):
    """Calidad y forma del modelo de un algoritmo."""

    algoritmo: str
    r2_entrenamiento: float  # sobre ln(tiempo)
    error_medio_pct: float  # en grafos nunca vistos
    exponente_nodos: float
    exponente_aristas: float


class Seleccion(NamedTuple):
    """Aciertos al elegir el algoritmo más rápido entre los correctos."""

    grafos: int
    aciertos_modelo: int
    aciertos_regla_fija: int  # siempre Dijkstra
    regla_fija: str


class Recomendacion(NamedTuple):
    """Algoritmo sugerido y tiempo predicho de cada candidato."""

    algoritmo: str
    predicciones_ms: dict[str, float]


class ResultadoPrediccion(NamedTuple):
    """Todo lo que produce entrenar y evaluar el modelo."""

    modelo: "ModeloTiempos"
    entrenamiento: int  # cantidad de muestras
    evaluaciones: list[Evaluacion]
    pruebas: list[FilaPrueba]
    seleccion: Seleccion


def medir_muestras(
    plan: Sequence[tuple[int, int]], consultas: int = CONSULTAS
) -> list[Muestra]:
    """Mide el tiempo medio por consulta de cada algoritmo en cada grafo.

    >>> muestras = medir_muestras([(100, 3)], consultas=2)
    >>> sorted(m.algoritmo for m in muestras)
    ['A*', 'BFS', 'Dijkstra']
    >>> all(m.tiempo_ms > 0 and m.aristas > 0 for m in muestras)
    True
    """
    muestras = []
    for nodos, vecinos in plan:
        grafo = generar_grafo(nodos, vecinos_por_nodo=vecinos)
        grafo.factor_heuristica()  # fuera de la medición, igual que el resto
        pares = generar_consultas(grafo, consultas, semilla=3)
        for nombre, algoritmo in ALGORITMOS.items():
            inicio = time.perf_counter()
            for origen, destino in pares:
                algoritmo(grafo, origen, destino)
            milisegundos = 1000 * (time.perf_counter() - inicio) / consultas
            muestras.append(
                Muestra(nodos, grafo.cantidad_aristas(), nombre, milisegundos)
            )
    return muestras


def advertencias(nodos: int, aristas: int) -> list[str]:
    """Avisos cuando la consulta cae fuera de lo que el modelo vio.

    Un modelo ajustado a cierto rango extrapola mal fuera de él.

    >>> advertencias(5_000, 15_000)
    []
    >>> [a.split(":")[0] for a in advertencias(100_000, 1_000_000)]
    ['Tamaño mayor que el entrenado', 'Densidad fuera de lo entrenado']
    """
    avisos = []
    if nodos > NODOS_ENTRENADOS:
        avisos.append(
            f"Tamaño mayor que el entrenado: el modelo vio hasta "
            f"{NODOS_ENTRENADOS:,} nodos; la predicción extrapola.".replace(
                ",", "."
            )
        )
    minima, maxima = DENSIDAD_ENTRENADA
    if not minima <= aristas / nodos <= maxima:
        avisos.append(
            f"Densidad fuera de lo entrenado: el modelo vio de {minima} a "
            f"{maxima} aristas por nodo."
        )
    return avisos


def _caracteristicas(nodos: int, aristas: int) -> list[float]:
    """Entradas del modelo: los logaritmos de nodos y aristas."""
    return [math.log(nodos), math.log(aristas)]


def _matriz(
    muestras: Sequence[Muestra], algoritmo: str
) -> tuple[list[list[float]], list[float]]:
    """Entradas y objetivo (ln del tiempo) de las muestras de un algoritmo."""
    propias = [m for m in muestras if m.algoritmo == algoritmo]
    return (
        [_caracteristicas(m.nodos, m.aristas) for m in propias],
        [math.log(m.tiempo_ms) for m in propias],
    )


def _error_pct(predicho: float, medido: float) -> float:
    """Error relativo de una predicción, en porcentaje.

    >>> _error_pct(12.0, 10.0)
    20.0
    """
    return 100 * abs(predicho - medido) / medido


class ModeloTiempos:
    """Un regresor por algoritmo: ``ln(tiempo) ~ ln(nodos) + ln(aristas)``.

    >>> muestras = [
    ...     Muestra(n, 3 * n, "BFS", 0.001 * n) for n in (100, 200, 400, 800)
    ... ]
    >>> modelo = ModeloTiempos().entrenar(muestras)
    >>> round(modelo.predecir("BFS", 1600, 4800), 1)
    1.6
    """

    def __init__(self) -> None:
        self.regresores: dict[str, LinearRegression] = {}

    def entrenar(self, muestras: Sequence[Muestra]) -> "ModeloTiempos":
        """Ajusta un regresor con las muestras de cada algoritmo."""
        for algoritmo in sorted({m.algoritmo for m in muestras}):
            self.regresores[algoritmo] = LinearRegression().fit(
                *_matriz(muestras, algoritmo)
            )
        return self

    def predecir(self, algoritmo: str, nodos: int, aristas: int) -> float:
        """Tiempo esperado en milisegundos de una consulta."""
        regresor = self.regresores[algoritmo]
        logaritmo = regresor.predict([_caracteristicas(nodos, aristas)])[0]
        return math.exp(logaritmo)

    def recomendar(
        self, nodos: int, aristas: int, ponderado: bool = True
    ) -> Recomendacion:
        """El algoritmo correcto con menor tiempo predicho.

        >>> muestras = [
        ...     Muestra(n, 3 * n, a, f * n)
        ...     for n in (100, 200, 400)
        ...     for a, f in (("Dijkstra", 1.0), ("A*", 2.0), ("BFS", 0.5))
        ... ]
        >>> modelo = ModeloTiempos().entrenar(muestras)
        >>> modelo.recomendar(800, 2400).algoritmo
        'Dijkstra'
        >>> modelo.recomendar(800, 2400, ponderado=False).algoritmo
        'BFS'
        """
        predicciones = {
            algoritmo: self.predecir(algoritmo, nodos, aristas)
            for algoritmo in CORRECTOS[ponderado]
        }
        mejor = min(predicciones, key=predicciones.__getitem__)
        return Recomendacion(mejor, predicciones)

    def evaluar(
        self, entrenamiento: Sequence[Muestra], prueba: Sequence[Muestra]
    ) -> list[Evaluacion]:
        """Calidad de cada regresor con grafos que no se usaron al entrenar."""
        evaluaciones = []
        for algoritmo, regresor in self.regresores.items():
            nuevas = [m for m in prueba if m.algoritmo == algoritmo]
            errores = [
                _error_pct(
                    self.predecir(algoritmo, m.nodos, m.aristas), m.tiempo_ms
                )
                for m in nuevas
            ]
            evaluaciones.append(
                Evaluacion(
                    algoritmo,
                    regresor.score(*_matriz(entrenamiento, algoritmo)),
                    sum(errores) / len(errores),
                    float(regresor.coef_[0]),
                    float(regresor.coef_[1]),
                )
            )
        return evaluaciones


def _evaluar_seleccion(
    modelo: ModeloTiempos, prueba: Sequence[Muestra]
) -> Seleccion:
    """Compara la elección del modelo con el algoritmo realmente más rápido."""
    grafos = sorted({(m.nodos, m.aristas) for m in prueba})
    aciertos_modelo = aciertos_regla = 0
    for nodos, aristas in grafos:
        medidos = {
            m.algoritmo: m.tiempo_ms
            for m in prueba
            if (m.nodos, m.aristas) == (nodos, aristas)
            and m.algoritmo in CORRECTOS[True]
        }
        mas_rapido = min(medidos, key=medidos.__getitem__)
        recomendado = modelo.recomendar(nodos, aristas).algoritmo
        aciertos_modelo += recomendado == mas_rapido
        aciertos_regla += mas_rapido == REGLA_FIJA
    return Seleccion(len(grafos), aciertos_modelo, aciertos_regla, REGLA_FIJA)


def entrenar_y_evaluar(
    plan_entrenamiento: Sequence[tuple[int, int]] = PLAN_ENTRENAMIENTO,
    plan_prueba: Sequence[tuple[int, int]] = PLAN_PRUEBA,
) -> ResultadoPrediccion:
    """Mide, entrena con un plan y evalúa con grafos que el modelo no vio.

    >>> r = entrenar_y_evaluar(((100, 2), (200, 3), (400, 4)), ((300, 3),))
    >>> len(r.evaluaciones), r.seleccion.grafos
    (3, 1)
    """
    entrenamiento = medir_muestras(plan_entrenamiento)
    prueba = medir_muestras(plan_prueba)
    modelo = ModeloTiempos().entrenar(entrenamiento)
    pruebas = []
    for m in prueba:
        predicho = modelo.predecir(m.algoritmo, m.nodos, m.aristas)
        pruebas.append(
            FilaPrueba(
                m.nodos,
                m.aristas,
                m.algoritmo,
                m.tiempo_ms,
                predicho,
                _error_pct(predicho, m.tiempo_ms),
            )
        )
    return ResultadoPrediccion(
        modelo,
        len(entrenamiento),
        modelo.evaluar(entrenamiento, prueba),
        pruebas,
        _evaluar_seleccion(modelo, prueba),
    )
