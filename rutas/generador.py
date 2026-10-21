"""Generación de grafos y consultas de prueba reproducibles."""

import math
import random

from rutas.grafo import Grafo

LADO_MAPA = 1000
Consulta = tuple[str, str]


def generar_grafo(
    cantidad_nodos: int, semilla: int = 1, vecinos_por_nodo: int = 3
) -> Grafo:
    """Crea un grafo geométrico conexo.

    Los nodos se ordenan por la coordenada x y cada uno se une con los
    siguientes, lo que garantiza conectividad. El peso es la distancia
    euclídea multiplicada por un factor aleatorio >= 1.

    >>> generar_grafo(100).nodos()[:3]
    ['0', '1', '2']
    >>> len(generar_grafo(50).adyacencia)
    50
    """
    azar = random.Random(semilla)
    puntos = sorted(
        (azar.uniform(0, LADO_MAPA), azar.uniform(0, LADO_MAPA))
        for _ in range(cantidad_nodos)
    )
    grafo = Grafo()
    for indice, (x, y) in enumerate(puntos):
        grafo.agregar_nodo(str(indice), x, y)
    for i in range(cantidad_nodos):
        ultimo = min(cantidad_nodos, i + vecinos_por_nodo + 1)
        for j in range(i + 1, ultimo):
            peso = math.dist(puntos[i], puntos[j]) * azar.uniform(1, 1.3)
            grafo.conectar(str(i), str(j), round(peso, 2))
    return grafo


def generar_consultas(
    grafo: Grafo, cantidad: int, semilla: int = 0
) -> list[Consulta]:
    """Devuelve pares (origen, destino) distintos elegidos al azar.

    Con la misma semilla el resultado es siempre el mismo:

    >>> g = generar_grafo(20)
    >>> generar_consultas(g, 3, 1) == generar_consultas(g, 3, 1)
    True
    """
    azar = random.Random(semilla)
    nodos = grafo.nodos()
    consultas: list[Consulta] = []
    for _ in range(cantidad):
        # Consultas reproducibles (semilla fija): no es criptografía.
        origen, destino = azar.sample(nodos, 2)  # NOSONAR
        consultas.append((origen, destino))
    return consultas


def preparar_escenario(
    cantidad_nodos: int, cantidad_consultas: int
) -> tuple[Grafo, list[Consulta]]:
    """Grafo y consultas reproducibles que comparten todos los perfiladores.

    >>> grafo, consultas = preparar_escenario(50, 3)
    >>> len(consultas)
    3
    """
    grafo = generar_grafo(cantidad_nodos, semilla=7)
    grafo.factor_heuristica()
    return grafo, generar_consultas(grafo, cantidad_consultas, semilla=4)
