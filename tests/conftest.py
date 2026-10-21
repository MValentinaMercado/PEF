"""Fixtures compartidas de pytest."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.estado import estado
from rutas.ejemplo import crear_grafo_ejemplo
from rutas.generador import generar_grafo


@pytest.fixture
def grafo_ejemplo():
    """Grafo pequeño donde BFS y Dijkstra difieren."""
    return crear_grafo_ejemplo()


@pytest.fixture(scope="module")
def grafo_mediano():
    """Grafo de 300 nodos reutilizado por varias pruebas."""
    return generar_grafo(300)


@pytest.fixture
def cliente():
    """Cliente HTTP con el grafo de ejemplo recién cargado."""
    estado.grafo = crear_grafo_ejemplo()
    return TestClient(app)
