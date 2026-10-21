"""Caché de rutas con memorización e invalidación automática."""

from rutas.algoritmos import ALGORITMOS, ResultadoBusqueda
from rutas.grafo import Grafo


class CacheRutas:
    """Memoriza rutas por (origen, destino) y se invalida al cambiar el grafo.

    Atributos:
        aciertos: consultas respondidas desde la caché.
        fallos: consultas que hubo que calcular.
        invalidaciones: veces que la caché se vació por un cambio del grafo.

    >>> from rutas.generador import generar_grafo
    >>> g, cache = generar_grafo(30), CacheRutas()
    >>> _ = cache.consultar(g, "0", "20"); _ = cache.consultar(g, "0", "20")
    >>> cache.aciertos, cache.fallos
    (1, 1)
    """

    def __init__(
        self, algoritmo: str = "Dijkstra", tamano_maximo: int = 2048
    ) -> None:
        self._algoritmo = ALGORITMOS[algoritmo]
        self._tamano_maximo = tamano_maximo
        self._entradas: dict[tuple[str, str], ResultadoBusqueda] = {}
        self._version_grafo: int | None = None
        self.aciertos = 0
        self.fallos = 0
        self.invalidaciones = 0

    def consultar(
        self, grafo: Grafo, origen: str, destino: str
    ) -> ResultadoBusqueda:
        """Devuelve la ruta, calculándola solo si no estaba memorizada."""
        if self._version_grafo != grafo.version:
            if self._entradas:
                self.invalidaciones += 1
            self._entradas.clear()
            self._version_grafo = grafo.version
        clave = (origen, destino)
        if clave in self._entradas:
            self.aciertos += 1
            return self._entradas[clave]
        self.fallos += 1
        resultado = self._algoritmo(grafo, origen, destino)
        if len(self._entradas) >= self._tamano_maximo:
            # Se descarta la entrada más antigua (los dict conservan orden).
            self._entradas.pop(next(iter(self._entradas)))
        self._entradas[clave] = resultado
        return resultado
