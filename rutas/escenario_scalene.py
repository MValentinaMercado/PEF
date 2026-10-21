"""Programa que Scalene perfila: los tres algoritmos con las mismas consultas.

Scalene perfila programas completos (no funciones sueltas), así que el
escenario es un script. Se ejecuta con::

    python -m scalene run rutas/escenario_scalene.py
"""

from rutas.algoritmos import ALGORITMOS
from rutas.generador import preparar_escenario


def ejecutar_escenario(
    cantidad_nodos: int = 5000, cantidad_consultas: int = 3000
) -> None:
    """Resuelve las consultas con cada algoritmo.

    Son más consultas que en cProfile para que Scalene, que muestrea el
    programa cada pocos milisegundos, junte suficientes muestras. En Windows
    Scalene 2.3 descarta el perfil si mide menos de un segundo de CPU y con
    150 consultas (2 s en total) no llegaba; con 600 dura unos 6-9 s.

    >>> ejecutar_escenario(100, 2)
    """
    grafo, consultas = preparar_escenario(cantidad_nodos, cantidad_consultas)
    for algoritmo in ALGORITMOS.values():
        for origen, destino in consultas:
            algoritmo(grafo, origen, destino)


if __name__ == "__main__":
    ejecutar_escenario()
