"""Memory Gate: controla el pico de memoria de Dijkstra."""

import os
import sys
import tracemalloc
from pathlib import Path

from rutas.algoritmos import dijkstra
from rutas.generador import generar_consultas, generar_grafo

LIMITE_MIB = 32
LIMITE_BYTES = LIMITE_MIB * 1024 * 1024
NODOS = 100_000
CONSULTAS = 5


def medir_pico_memoria(nodos: int = NODOS) -> int:
    """Devuelve el pico de memoria rastreada durante las consultas."""
    grafo = generar_grafo(nodos)
    consultas = generar_consultas(grafo, CONSULTAS)

    tracemalloc.start()
    try:
        for origen, destino in consultas:
            dijkstra(grafo, origen, destino)
        _, pico = tracemalloc.get_traced_memory()
        return pico
    finally:
        tracemalloc.stop()


def aprobado(pico_bytes: int, limite_bytes: int = LIMITE_BYTES) -> bool:
    """Indica si el pico no supera el límite configurado."""
    return pico_bytes <= limite_bytes


def _agregar_al_resumen(texto: str) -> None:
    """Agrega el resultado al resumen de GitHub Actions."""
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        with Path(ruta).open("a", encoding="utf-8") as archivo:
            archivo.write(f"### Memory Gate\n\n{texto}\n")


def main() -> int:
    """Ejecuta el control de memoria y devuelve el código de salida."""
    pico = medir_pico_memoria()
    cumple = aprobado(pico)
    resultado = "PASSED" if cumple else "FAILED"
    texto = (
        f"Memory Gate {resultado}: pico de {pico / (1024 * 1024):.2f} MiB; "
        f"límite {LIMITE_MIB} MiB."
    )
    print(texto)
    _agregar_al_resumen(texto)
    return 0 if cumple else 1


if __name__ == "__main__":
    sys.exit(main())