"""Performance Gate: falla si Dijkstra supera el tiempo límite.

Se ejecuta en el pipeline de integración continua con::

    python -m rutas.performance_gate

Genera un grafo reproducible de 100.000 nodos, resuelve las mismas consultas
varias veces y compara la **mediana** del tiempo por consulta con un umbral.
Si la supera imprime ``Performance Gate FAILED`` y termina con código 1, lo
que hace fallar el pipeline.

Por qué 500 ms: en una PC de desarrollo Dijkstra tarda unos 150 ms por
consulta en este grafo. Los runners de GitHub Actions suelen ser entre 1,5 y
2,5 veces más lentos, así que 500 ms deja margen para el ruido sin ocultar
una regresión real: usar una lista en vez de un conjunto para los nodos
cerrados lo vuelve cuadrático y lo lleva a varios segundos. Se usa la
mediana y no el promedio para que una corrida aislada lenta no tumbe el
pipeline.
"""

import argparse
import os
import statistics
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from rutas.algoritmos import dijkstra
from rutas.generador import Consulta, generar_consultas, generar_grafo
from rutas.grafo import Grafo

NODOS = 100_000
CONSULTAS = 5
REPETICIONES = 3
UMBRAL_MS = 500.0
# Si una sola corrida supera FACTOR_CORTE veces el umbral se deja de medir:
# la regresión ya es evidente y no hace falta esperar el resto.
FACTOR_CORTE = 10


def medir_ms(
    grafo: Grafo,
    consultas: Sequence[Consulta],
    repeticiones: int,
    corte_ms: float,
) -> list[float]:
    """Tiempo en ms de cada corrida de Dijkstra.

    Se detiene en cuanto una corrida supera ``corte_ms``.

    >>> grafo = generar_grafo(100)
    >>> consultas = generar_consultas(grafo, 2)
    >>> len(medir_ms(grafo, consultas, 3, corte_ms=1e9))
    6
    >>> len(medir_ms(grafo, consultas, 3, corte_ms=0.0))
    1
    """
    tiempos: list[float] = []
    for origen, destino in consultas:
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            dijkstra(grafo, origen, destino)
            tiempos.append((time.perf_counter() - inicio) * 1000)
            if tiempos[-1] > corte_ms:
                return tiempos
    return tiempos


def aprobado(mediana_ms: float, umbral_ms: float) -> bool:
    """El gate se cumple si la mediana es menor que el umbral.

    >>> aprobado(150.0, 500.0)
    True
    >>> aprobado(500.0, 500.0)
    False
    """
    return mediana_ms < umbral_ms


def _leer_argumentos(argv: Sequence[str] | None) -> argparse.Namespace:
    """Opciones de línea de comandos (por defecto, las del pipeline)."""
    analizador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analizador.add_argument("--nodos", type=int, default=NODOS)
    analizador.add_argument("--umbral-ms", type=float, default=UMBRAL_MS)
    return analizador.parse_args(argv)


def _agregar_al_resumen(texto: str) -> None:
    """En GitHub Actions deja el resultado en el resumen de la corrida."""
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        with Path(ruta).open("a", encoding="utf-8") as archivo:
            archivo.write(f"### Performance Gate\n\n{texto}\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Mide, informa y devuelve el código de salida (0 aprobado, 1 falla)."""
    args = _leer_argumentos(argv)
    grafo = generar_grafo(args.nodos)
    consultas = generar_consultas(grafo, CONSULTAS)
    tiempos = medir_ms(
        grafo, consultas, REPETICIONES, args.umbral_ms * FACTOR_CORTE
    )
    mediana = statistics.median(tiempos)
    cumple = aprobado(mediana, args.umbral_ms)
    resultado = "PASSED" if cumple else "FAILED"
    texto = (
        f"Performance Gate {resultado}: Dijkstra tardó {mediana:.1f} ms "
        f"(mediana de {len(tiempos)} corridas, máximo {max(tiempos):.1f} ms) "
        f"con {args.nodos} nodos; límite {args.umbral_ms:.0f} ms."
    )
    print(texto)
    _agregar_al_resumen(texto)
    return 0 if cumple else 1


if __name__ == "__main__":
    sys.exit(main())
