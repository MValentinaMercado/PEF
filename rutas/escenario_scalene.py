"""Programa que Scalene perfila: los tres algoritmos con las mismas consultas.

Scalene perfila programas completos (no funciones sueltas), así que el
escenario es un script. Se ejecuta con::

    python -m scalene run rutas/escenario_scalene.py
"""

from rutas.algoritmos import ALGORITMOS
from rutas.generador import preparar_escenario


def ejecutar_escenario(
    cantidad_nodos: int = 5000, cantidad_consultas: int = 150
) -> None:
    """Resuelve las consultas con cada algoritmo.

    Son más consultas que en cProfile para que Scalene, que muestrea el
    programa cada pocos milisegundos, junte suficientes muestras.

    >>> ejecutar_escenario(100, 2)
    """
    grafo, consultas = preparar_escenario(cantidad_nodos, cantidad_consultas)
    for algoritmo in ALGORITMOS.values():
        for origen, destino in consultas:
            algoritmo(grafo, origen, destino)


if __name__ == "__main__":
    ejecutar_escenario()
