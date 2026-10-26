"""Pruebas de la ventana Optimización (herramientas de limpieza)."""

import json
import subprocess

import pytest

from api import optimizacion_router

CLAVES = {"herramienta", "criterio", "cumple", "total", "filas", "fichas"}


def _proceso(salida: str = "", codigo: int = 0, error: str = ""):
    return subprocess.CompletedProcess([], codigo, salida, error)


def test_pagina_optimizacion_se_sirve(cliente):
    respuesta = cliente.get("/optimizacion")
    assert respuesta.status_code == 200
    assert "Herramientas de limpieza" in respuesta.text


@pytest.mark.parametrize("herramienta", ["ruff", "vulture", "radon"])
def test_proyecto_cumple_los_criterios_de_limpieza(cliente, herramienta):
    datos = cliente.post(f"/api/optimizacion/{herramienta}").json()
    assert datos.keys() >= CLAVES
    assert datos["cumple"] is True, datos["filas"]


def test_pylint_devuelve_el_formato_comun(cliente):
    datos = cliente.post("/api/optimizacion/pylint").json()
    assert datos.keys() >= CLAVES
    assert datos["total"] == len(datos["filas"])
    assert datos["cumple"] == (datos["total"] == 0)


def test_radon_informa_complejidad_y_mantenibilidad(cliente):
    datos = cliente.post("/api/optimizacion/radon").json()
    titulos = [ficha["titulo"] for ficha in datos["fichas"]]
    assert titulos[0] == "complejidad promedio"
    assert len(datos["filas"]) <= 5
    complejidades = [fila["complejidad"] for fila in datos["filas"]]
    assert complejidades == sorted(complejidades, reverse=True)


def test_herramienta_desconocida_se_rechaza(cliente):
    assert cliente.post("/api/optimizacion/inexistente").status_code == 422


def test_cobertura_lista_las_lineas_sin_ejecutar(cliente, monkeypatch):
    informe = {
        "totals": {"missing_lines": 3},
        "files": {"api/x.py": {"missing_lines": [4, 5, 9]}},
    }

    def falso(*argumentos, **_):
        ruta = next(a for a in argumentos if a.startswith("--cov-report="))
        with open(ruta.split("json:")[1], "w", encoding="utf-8") as f:
            json.dump(informe, f)
        return _proceso()

    monkeypatch.setattr(optimizacion_router, "correr_pytest", falso)
    datos = cliente.post("/api/optimizacion/cobertura").json()
    assert datos["total"] == 3
    assert datos["cumple"] is None
    assert [f["mensaje"] for f in datos["filas"]] == ["líneas 4-5", "línea 9"]


def test_cobertura_sin_informe_da_error(cliente, monkeypatch):
    monkeypatch.setattr(
        optimizacion_router, "correr_pytest", lambda *a, **k: _proceso()
    )
    assert cliente.post("/api/optimizacion/cobertura").status_code == 500


def test_herramienta_no_instalada_da_error(cliente, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _proceso("", 1, "No module named vulture"),
    )
    respuesta = cliente.post("/api/optimizacion/vulture")
    assert respuesta.status_code == 500
    assert "no se pudo ejecutar" in respuesta.json()["detail"]


def test_herramienta_lenta_da_error_de_tiempo(cliente, monkeypatch):
    def lento(*_, **__):
        raise subprocess.TimeoutExpired("vulture", 1)

    monkeypatch.setattr(subprocess, "run", lento)
    assert cliente.post("/api/optimizacion/vulture").status_code == 504


def test_hallazgos_pylint_ignora_otros_mensajes():
    texto = json.dumps(
        {"messages": [{"symbol": "line-too-long", "message": "x"}]}
    )
    assert optimizacion_router.hallazgos_pylint(texto) == []
