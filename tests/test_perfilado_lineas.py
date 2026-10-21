"""Pruebas de line_profiler y Scalene (ventana Análisis, perfilado)."""

import subprocess

import pytest

from api import analisis_router
from rutas import perfilado_scalene
from rutas.perfilado import ejecutar_perfilado_lineas
from rutas.perfilado_scalene import (
    FilaScalene,
    ResultadoScalene,
    ejecutar_scalene,
)


def test_line_profiler_mide_cada_algoritmo():
    perfiles = ejecutar_perfilado_lineas(300, 3)
    assert set(perfiles) == {"BFS", "Dijkstra", "A*"}
    for filas in perfiles.values():
        assert filas
        assert round(sum(f.porcentaje for f in filas)) == 100
        assert all(f.ejecuciones > 0 and f.codigo for f in filas)


def test_dijkstra_ejecuta_el_heap_una_vez_por_extraccion():
    filas = ejecutar_perfilado_lineas(300, 3)["Dijkstra"]
    codigo = {f.codigo: f.ejecuciones for f in filas}
    extracciones = codigo["_, costo_actual, actual = heapq.heappop(heap)"]
    assert extracciones >= codigo["cerrados.add(actual)"] > 0


def test_endpoint_lineas_devuelve_una_tabla_por_algoritmo(cliente):
    datos = cliente.post("/api/analisis/lineas").json()
    assert set(datos) == {"BFS", "Dijkstra", "A*"}
    assert {"linea", "ejecuciones", "porcentaje", "codigo"} <= set(
        datos["Dijkstra"][0]
    )


def test_endpoint_scalene_devuelve_resumen_y_filas(cliente, monkeypatch):
    fila = FilaScalene("rutas/x.py", 3, 10.0, 2.0, 0.0, 1.5, "x = 1")
    monkeypatch.setattr(
        analisis_router,
        "ejecutar_scalene",
        lambda: ResultadoScalene(2.5, 18.0, 0.99, [fila]),
    )
    datos = cliente.post("/api/analisis/scalene").json()
    assert datos["segundos"] == 2.5
    assert datos["filas"][0]["archivo"] == "rutas/x.py"


def test_endpoint_scalene_informa_el_error(cliente, monkeypatch):
    def falla():
        raise RuntimeError("Scalene no está instalado")

    monkeypatch.setattr(analisis_router, "ejecutar_scalene", falla)
    respuesta = cliente.post("/api/analisis/scalene")
    assert respuesta.status_code == 500
    assert "Scalene" in respuesta.json()["detail"]


def test_scalene_sin_perfil_da_error(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 1, "", "boom"),
    )
    with pytest.raises(RuntimeError, match="no generó el perfil"):
        ejecutar_scalene()


def test_scalene_lento_da_error(monkeypatch):
    def lento(*_, **__):
        raise subprocess.TimeoutExpired("scalene", 1)

    monkeypatch.setattr(subprocess, "run", lento)
    with pytest.raises(RuntimeError, match="tardó demasiado"):
        ejecutar_scalene()


def test_scalene_real_perfila_el_proyecto():
    pytest.importorskip("scalene")
    resultado = ejecutar_scalene()
    assert resultado.segundos > 0
    archivos = {f.archivo for f in resultado.filas}
    assert any(a.startswith("rutas/algoritmos/") for a in archivos)
    assert perfilado_scalene.ESCENARIO.name not in " ".join(archivos)
