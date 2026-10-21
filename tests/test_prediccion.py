"""Pruebas del componente de IA: regresión que predice tiempos."""

import pytest

from api import analisis_router
from api.estado import estado
from rutas import prediccion
from rutas.prediccion import (
    ModeloTiempos,
    Muestra,
    advertencias,
    entrenar_y_evaluar,
)


def _muestras_sinteticas() -> list[Muestra]:
    """Tiempos que siguen exactamente t = k * V * E^0,5 (sin ruido)."""
    return [
        Muestra(n, n * vecinos, "Dijkstra", 1e-4 * n * (n * vecinos) ** 0.5)
        for n in (100, 200, 400, 800)
        for vecinos in (2, 4)
    ]


def test_el_modelo_recupera_los_exponentes_de_una_relacion_conocida():
    modelo = ModeloTiempos().entrenar(_muestras_sinteticas())
    b, c = modelo.regresores["Dijkstra"].coef_
    assert b == pytest.approx(1.0, abs=1e-6)
    assert c == pytest.approx(0.5, abs=1e-6)


def test_la_prediccion_acierta_fuera_del_rango_entrenado():
    muestras = _muestras_sinteticas()
    modelo = ModeloTiempos().entrenar(muestras)
    nueva = Muestra(5000, 15000, "Dijkstra", 1e-4 * 5000 * 15000**0.5)
    evaluacion = modelo.evaluar(muestras, [nueva])[0]
    assert evaluacion.error_medio_pct < 1e-6
    assert evaluacion.r2_entrenamiento == pytest.approx(1.0)


def test_bfs_solo_se_recomienda_sin_pesos():
    muestras = [
        Muestra(n, 3 * n, algoritmo, factor * n)
        for n in (100, 200, 400)
        for algoritmo, factor in (("BFS", 0.1), ("Dijkstra", 1), ("A*", 2))
    ]
    modelo = ModeloTiempos().entrenar(muestras)
    assert modelo.recomendar(1000, 3000, ponderado=True).algoritmo != "BFS"
    assert modelo.recomendar(1000, 3000, ponderado=False).algoritmo == "BFS"


def test_advertencia_fuera_del_rango_entrenado():
    assert advertencias(5_000, 15_000) == []
    assert len(advertencias(100_000, 300_000)) == 1
    assert len(advertencias(100_000, 2_000_000)) == 2


def test_entrenar_y_evaluar_mide_con_datos_reales():
    resultado = entrenar_y_evaluar(
        ((100, 2), (200, 3), (400, 4), (800, 3)), ((300, 3), (600, 4))
    )
    assert resultado.entrenamiento == 12
    assert {e.algoritmo for e in resultado.evaluaciones} == {
        "BFS",
        "Dijkstra",
        "A*",
    }
    assert len(resultado.pruebas) == 6
    assert resultado.seleccion.grafos == 2
    assert all(f.predicho_ms > 0 for f in resultado.pruebas)


@pytest.fixture
def modelo_reducido(monkeypatch):
    """Entrena con un plan chico para que el endpoint responda rápido."""
    monkeypatch.setattr(estado, "modelo", None)

    def reducido():
        return prediccion.entrenar_y_evaluar(
            ((100, 2), (200, 3), (400, 4), (800, 3)), ((300, 3),)
        )

    monkeypatch.setattr(analisis_router, "entrenar_y_evaluar", reducido)


def test_recomendar_pide_entrenar_primero(cliente, modelo_reducido):
    respuesta = cliente.get(
        "/api/analisis/prediccion/recomendar?nodos=1000&aristas=3000"
    )
    assert respuesta.status_code == 409


def test_endpoint_entrena_y_luego_recomienda(cliente, modelo_reducido):
    datos = cliente.post("/api/analisis/prediccion").json()
    assert datos["entrenamiento"] == 12
    assert set(datos) == {
        "entrenamiento",
        "evaluaciones",
        "pruebas",
        "seleccion",
    }
    respuesta = cliente.get(
        "/api/analisis/prediccion/recomendar?nodos=100000&aristas=300000"
    ).json()
    assert respuesta["algoritmo"] in ("Dijkstra", "A*")
    assert set(respuesta["predicciones_ms"]) == {"Dijkstra", "A*"}
    assert respuesta["advertencias"]  # 100.000 nodos supera lo entrenado


@pytest.mark.parametrize(
    "consulta", ["nodos=1&aristas=3", "nodos=10&aristas=0", "aristas=3"]
)
def test_recomendar_rechaza_valores_invalidos(cliente, consulta):
    ruta = f"/api/analisis/prediccion/recomendar?{consulta}"
    assert cliente.get(ruta).status_code == 422
