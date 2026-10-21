"""Pruebas de la caché de rutas."""

import unittest

from rutas.cache import CacheRutas
from tests.test_algoritmos import construir_grafo_ejemplo


class PruebasCache(unittest.TestCase):
    """Verifica aciertos, fallos e invalidación."""

    def test_repetir_consulta_es_acierto(self):
        grafo, cache = construir_grafo_ejemplo(), CacheRutas()
        cache.consultar(grafo, "A", "D")
        cache.consultar(grafo, "A", "D")
        self.assertEqual((cache.fallos, cache.aciertos), (1, 1))

    def test_cambio_del_grafo_invalida(self):
        grafo, cache = construir_grafo_ejemplo(), CacheRutas()
        antes = cache.consultar(grafo, "A", "D")
        grafo.conectar("A", "D", 0.5)
        despues = cache.consultar(grafo, "A", "D")
        self.assertEqual(cache.invalidaciones, 1)
        self.assertNotEqual(antes.distancia, despues.distancia)


if __name__ == "__main__":
    unittest.main()
