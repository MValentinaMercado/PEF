"""Memory Gate: falla si Dijkstra supera el límite de memoria.

Se ejecuta en el pipeline de integración continua con::

    python -m rutas.memory_gate

Genera el mismo grafo reproducible de 100.000 nodos que el Performance Gate,
mide con ``tracemalloc`` el pico de memoria de cada consulta y compara el
**mayor** con un límite. Si lo supera imprime ``Memory Gate FAILED`` y
termina con código 1, lo que hace fallar el pipeline.

El límite de 32 MiB es una política del proyecto, no una afirmación sobre
el consumo actual de todas las máquinas. El valor medido se informa en cada
corrida; ``tracemalloc`` permite comparar las asignaciones de Python con un
criterio estable dentro del mismo entorno. El límite se puede ajustar con
``--limite-mib``.
"""

import argparse
import sys
from collections.abc import Sequence

from rutas.algoritmos import dijkstra
from rutas.generador import Consulta, generar_consultas, generar_grafo
from rutas.grafo import Grafo
from rutas.mediciones import medir_consulta
from rutas.performance_gate import agregar_al_resumen

NODOS = 100_000
CONSULTAS = 5
LIMITE_MIB = 32.0
KB_POR_MIB = 1024


def pico_mib(grafo: Grafo, consultas: Sequence[Consulta]) -> float:
    """Mayor pico de memoria (en MiB) de Dijkstra entre las consultas.

    >>> grafo = generar_grafo(100)
    >>> consultas = generar_consultas(grafo, 2)
    >>> 0 < pico_mib(grafo, consultas) < 1
    True
    """
    picos = [
        medir_consulta(dijkstra, grafo, origen, destino).memoria_kb
        for origen, destino in consultas
    ]
    return max(picos) / KB_POR_MIB


def dentro_del_limite(pico: float, limite: float) -> bool:
    """El gate se cumple si el pico no supera el límite.

    >>> dentro_del_limite(20.0, 32.0)
    True
    >>> dentro_del_limite(32.0, 32.0)
    True
    >>> dentro_del_limite(32.1, 32.0)
    False
    """
    return pico <= limite


def _leer_argumentos(argv: Sequence[str] | None) -> argparse.Namespace:
    """Opciones de línea de comandos (por defecto, las del pipeline)."""
    analizador = argparse.ArgumentParser(description="Memory Gate")
    analizador.add_argument("--nodos", type=int, default=NODOS)
    analizador.add_argument("--limite-mib", type=float, default=LIMITE_MIB)
    return analizador.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Mide, informa y devuelve el código de salida (0 aprobado, 1 falla)."""
    args = _leer_argumentos(argv)
    grafo = generar_grafo(args.nodos)
    pico = pico_mib(grafo, generar_consultas(grafo, CONSULTAS))
    cumple = dentro_del_limite(pico, args.limite_mib)
    veredicto = "PASSED" if cumple else "FAILED"
    texto = (
        f"Memory Gate {veredicto}: Dijkstra llegó a {pico:.1f} MiB de pico "
        f"con {args.nodos} nodos; límite {args.limite_mib:.0f} MiB."
    )
    print(texto)
    agregar_al_resumen(texto, titulo="Memory Gate")
    return 0 if cumple else 1


if __name__ == "__main__":
    sys.exit(main())
