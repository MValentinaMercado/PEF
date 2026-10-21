"""Pruebas de line_profiler y Scalene (ventana Análisis, perfilado)."""

import json
import subprocess
from pathlib import Path

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


def _scalene_falso(perfiles, llamadas):
    """``ejecutar_modulo`` falso: escribe el siguiente perfil de la lista."""

    def falso(modulo, *argumentos, **_):
        llamadas.append(argumentos)
        destino = argumentos[argumentos.index("-o") + 1]
        Path(destino).write_text(perfiles.pop(0), encoding="utf-8")
        return subprocess.CompletedProcess([], 0, "", "no hubo muestras")

    return falso


def _perfil_con_una_linea():
    linea = {
        "lineno": 7,
        "line": "x = 1\n",
        "n_cpu_percent_python": 40.0,
        "n_cpu_percent_c": 5.0,
        "n_sys_percent": 0.0,
        "n_peak_mb": 0.0,
    }
    archivo = str(perfilado_scalene.RAIZ / "rutas" / "a.py")
    return json.dumps(
        {
            "elapsed_time_sec": 3.0,
            "max_footprint_mb": 0,
            "max_footprint_python_fraction": 0,
            "files": {archivo: {"lines": [linea]}},
        }
    )


def test_scalene_se_ejecuta_con_profile_all(monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        perfilado_scalene,
        "ejecutar_modulo",
        _scalene_falso([_perfil_con_una_linea()], llamadas),
    )
    resultado = ejecutar_scalene()
    assert "--profile-all" in llamadas[0]
    assert [f.archivo for f in resultado.filas] == ["rutas/a.py"]


def test_scalene_descarta_el_entorno_virtual_del_proyecto():
    linea = {
        "lineno": 1,
        "line": "x = 1\n",
        "n_cpu_percent_python": 50.0,
        "n_cpu_percent_c": 0.0,
        "n_sys_percent": 0.0,
        "n_peak_mb": 0.0,
    }
    raiz = perfilado_scalene.RAIZ
    datos = {
        "elapsed_time_sec": 1.0,
        "max_footprint_mb": 1.0,
        "max_footprint_python_fraction": 1.0,
        "files": {
            str(raiz / "rutas" / "grafo.py"): {"lines": [linea]},
            str(raiz / ".venv" / "Lib" / "site-packages" / "x.py"): {
                "lines": [linea]
            },
        },
    }
    resultado = perfilado_scalene.resumir_scalene(json.dumps(datos))
    assert [f.archivo for f in resultado.filas] == ["rutas/grafo.py"]


def test_scalene_si_siempre_sale_vacio_muestra_su_salida(monkeypatch):
    monkeypatch.setattr(
        perfilado_scalene,
        "ejecutar_modulo",
        _scalene_falso(["{}", "{}"], []),
    )
    with pytest.raises(RuntimeError, match="no hubo muestras"):
        ejecutar_scalene()


def test_scalene_perfil_vacio_da_error_claro():
    with pytest.raises(RuntimeError, match="perfil vacío"):
        perfilado_scalene.resumir_scalene("{}")


def test_scalene_real_perfila_el_proyecto():
    pytest.importorskip("scalene")
    try:
        resultado = ejecutar_scalene()
    except RuntimeError as error:
        # Scalene no puede medir en todos los sistemas (p. ej. Windows).
        pytest.skip(f"Scalene no pudo perfilar en este entorno: {error}")
    assert resultado.segundos > 0
    archivos = {f.archivo for f in resultado.filas}
    assert any(a.startswith("rutas/algoritmos/") for a in archivos)
    assert perfilado_scalene.ESCENARIO.name not in " ".join(archivos)
