"""Grafo no dirigido y ponderado con soporte para bloquear conexiones."""

import math
from collections.abc import Iterable

Pesos = dict[str, float]


class Grafo:
    """Grafo representado con listas de adyacencia basadas en ``dict``.

    >>> g = Grafo()
    >>> g.agregar_nodo("A"); g.agregar_nodo("B", 3, 4)
    >>> g.conectar("A", "B", 5)
    >>> g.adyacencia
    {'A': {'B': 5}, 'B': {'A': 5}}

    Atributos:
        adyacencia: ``{nodo: {vecino: peso}}``; acceso O(1) a nodos y
            vecinos, espacio O(V + E).
        posiciones: coordenadas ``(x, y)`` de cada nodo (para dibujar y
            para la heurística de A*).
        bloqueadas: conexiones deshabilitadas, guardadas en ambos sentidos.
        version: contador que aumenta con cada cambio; la caché lo usa
            para detectar resultados obsoletos.
    """

    def __init__(self) -> None:
        self.adyacencia: dict[str, Pesos] = {}
        self.posiciones: dict[str, tuple[float, float]] = {}
        self.bloqueadas: set[tuple[str, str]] = set()
        self.version = 0
        # (versión, factor): se recalcula solo si el grafo cambió.
        self._factor_cache: tuple[int, float] | None = None

    def agregar_nodo(
        self, nombre: str, x: float = 0.0, y: float = 0.0
    ) -> None:
        """Crea un nodo si todavía no existe."""
        if nombre not in self.adyacencia:
            self.adyacencia[nombre] = {}
            self.posiciones[nombre] = (x, y)
            self.version += 1

    def mover_nodo(self, nombre: str, x: float, y: float) -> None:
        """Cambia la posición de un nodo."""
        self.posiciones[nombre] = (x, y)
        self.version += 1

    def renombrar_nodo(self, actual: str, nuevo: str) -> bool:
        """Renombra un nodo; devuelve False si el cambio no es posible.

        >>> g = Grafo(); g.agregar_nodo("A"); g.agregar_nodo("B")
        >>> g.conectar("A", "B", 1)
        >>> g.renombrar_nodo("A", "Z"), g.renombrar_nodo("Z", "B")
        (True, False)
        >>> g.adyacencia["B"]
        {'Z': 1}
        """
        if actual not in self.adyacencia or nuevo in self.adyacencia:
            return False
        self.adyacencia[nuevo] = self.adyacencia.pop(actual)
        self.posiciones[nuevo] = self.posiciones.pop(actual)
        for vecino in self.adyacencia[nuevo]:
            pesos = self.adyacencia[vecino]
            pesos[nuevo] = pesos.pop(actual)
        self.bloqueadas = {
            (
                nuevo if origen == actual else origen,
                nuevo if destino == actual else destino,
            )
            for origen, destino in self.bloqueadas
        }
        self.version += 1
        return True

    def eliminar_nodo(self, nombre: str) -> None:
        """Elimina un nodo junto con todas sus conexiones."""
        for vecino in list(self.adyacencia.get(nombre, {})):
            self.eliminar_arista(nombre, vecino)
        self.adyacencia.pop(nombre, None)
        self.posiciones.pop(nombre, None)
        self.version += 1

    def conectar(self, a: str, b: str, peso: float) -> None:
        """Crea (o actualiza) la conexión entre ``a`` y ``b``.

        >>> g = Grafo(); g.agregar_nodo("A"); g.agregar_nodo("B")
        >>> g.conectar("A", "B", 2); g.conectar("A", "A", 1)
        >>> g.adyacencia["A"]
        {'B': 2}
        """
        if a != b and a in self.adyacencia and b in self.adyacencia:
            self.adyacencia[a][b] = peso
            self.adyacencia[b][a] = peso
            self.version += 1

    def eliminar_arista(self, a: str, b: str) -> None:
        """Elimina la conexión entre ``a`` y ``b``."""
        self.adyacencia[a].pop(b, None)
        self.adyacencia[b].pop(a, None)
        self.bloqueadas.discard((a, b))
        self.bloqueadas.discard((b, a))
        self.version += 1

    def establecer_bloqueo(self, a: str, b: str, bloqueada: bool) -> None:
        """Bloquea o habilita una conexión para simular cortes.

        >>> g = Grafo(); g.agregar_nodo("A"); g.agregar_nodo("B")
        >>> g.conectar("A", "B", 1); g.establecer_bloqueo("B", "A", True)
        >>> g.esta_bloqueada("A", "B"), list(g.vecinos_habilitados("A"))
        (True, [])
        """
        for par in ((a, b), (b, a)):
            if bloqueada:
                self.bloqueadas.add(par)
            else:
                self.bloqueadas.discard(par)
        self.version += 1

    def esta_bloqueada(self, a: str, b: str) -> bool:
        """Indica si la conexión ``a``-``b`` está bloqueada."""
        return (a, b) in self.bloqueadas

    def vecinos_habilitados(self, nodo: str) -> Iterable[tuple[str, float]]:
        """Devuelve los pares ``(vecino, peso)`` sin conexiones bloqueadas."""
        if not self.bloqueadas:
            return self.adyacencia[nodo].items()
        return [
            (vecino, peso)
            for vecino, peso in self.adyacencia[nodo].items()
            if (nodo, vecino) not in self.bloqueadas
        ]

    def nombre_libre(self) -> str:
        """Siguiente nombre sin usar: A, B, ... Z, N26, N27, ...

        >>> g = Grafo(); g.agregar_nodo("A"); g.nombre_libre()
        'B'
        """
        indice = len(self.adyacencia)
        while True:
            nombre = chr(65 + indice) if indice < 26 else f"N{indice}"
            if nombre not in self.adyacencia:
                return nombre
            indice += 1

    def cantidad_aristas(self) -> int:
        """Cantidad de aristas (cada una se guarda en ambos sentidos).

        >>> g = Grafo()
        >>> for nombre in "ab":
        ...     g.agregar_nodo(nombre, 0, 0)
        >>> g.conectar("a", "b", 1.0)
        >>> g.cantidad_aristas()
        1
        """
        return sum(len(vecinos) for vecinos in self.adyacencia.values()) // 2

    def nodos(self) -> list[str]:
        """Lista de nombres de nodos."""
        return list(self.adyacencia)

    def factor_heuristica(self) -> float:
        """Factor que vuelve admisible la heurística euclídea de A*.

        Es el mínimo de ``peso / distancia_dibujada`` entre todas las
        aristas: así ``factor * distancia`` nunca sobreestima el costo
        real, aunque los pesos no coincidan con el dibujo.
        """
        if self._factor_cache and self._factor_cache[0] == self.version:
            return self._factor_cache[1]
        minimo = math.inf
        for a, vecinos in self.adyacencia.items():
            for b, peso in vecinos.items():
                distancia = math.dist(self.posiciones[a], self.posiciones[b])
                if distancia > 0:
                    minimo = min(minimo, peso / distancia)
        factor = 0.0 if minimo == math.inf else minimo
        self._factor_cache = (self.version, factor)
        return factor
