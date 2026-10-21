"""Pruebas de la ventana de calidad (Ruff, cobertura y condiciones)."""

import json
import subprocess

from api import calidad_router

HALLAZGO = {
    "code": "F401",
    "message": "`os` importado pero sin usar",
    "filename": str(calidad_router.RAIZ / "api" / "x.py"),
    "location": {"row": 1, "column": 8},
}


def _proceso(salida: str = "", codigo: int = 0, error: str = ""):
    return subprocess.CompletedProcess([], codigo, salida, error)


def test_pagina_calidad_se_sirve(cliente):
    respuesta = cliente.get("/calidad")
    assert respuesta.status_code == 200
    assert "Análisis de calidad" in respuesta.text


def test_umbral_cobertura_sale_de_pyproject():
    assert 0 < calidad_router.umbral_cobertura() <= 100


def test_lint_con_hallazgos_incumple_las_condiciones(cliente, monkeypatch):
    def falso(*argumentos):
        if argumentos[0] == "check":
            return _proceso(json.dumps([HALLAZGO]), 1)
        if argumentos[0] == "format":
            return _proceso("Would reformat: rutas/grafo.py\n", 1)
        return _proceso("ruff 0.0.0")

    monkeypatch.setattr(calidad_router, "_ruff", falso)
    datos = cliente.post("/api/calidad/lint").json()
    assert datos["calidad"]["total"] == 1
    assert datos["calidad"]["hallazgos"][0]["archivo"] == "api/x.py"
    assert datos["sin_formato"] == ["rutas/grafo.py"]
    assert [c["ok"] for c in datos["condiciones"]] == [False, False]


def test_lint_limpio_cumple_las_condiciones(cliente, monkeypatch):
    monkeypatch.setattr(calidad_router, "_ruff", lambda *a: _proceso("[]"))
    datos = cliente.post("/api/calidad/lint").json()
    assert datos["calidad"]["total"] == 0
    assert all(c["ok"] for c in datos["condiciones"])


def test_lint_informa_si_ruff_no_esta_instalado(cliente, monkeypatch):
    monkeypatch.setattr(
        calidad_router,
        "_ruff",
        lambda *a: _proceso("", 2, "No module named ruff"),
    )
    respuesta = cliente.post("/api/calidad/lint")
    assert respuesta.status_code == 500
    assert "Ruff" in respuesta.json()["detail"]


def test_ruff_real_responde(cliente):
    """Humo: Ruff está instalado y la ventana recibe la estructura esperada."""
    datos = cliente.post("/api/calidad/lint").json()
    assert datos["herramienta"].startswith("ruff")
    assert {"calidad", "sin_formato", "condiciones"} <= set(datos)


def _pytest_falso(porcentaje: float, fallos: int):
    """Imita a ``pytest --cov``: escribe los dos informes que lee la API."""

    def ejecutar(comando, **_):
        cov = next(a for a in comando if a.startswith("--cov-report=json:"))
        xml = next(a for a in comando if a.startswith("--junitxml="))
        archivos = {
            "rutas/grafo.py": {
                "summary": {
                    "num_statements": 10,
                    "missing_lines": 2,
                    "percent_covered": 80.0,
                }
            }
        }
        cuerpo = {"totals": {"percent_covered": porcentaje}, "files": archivos}
        from pathlib import Path

        Path(cov.split(":", 1)[1]).write_text(
            json.dumps(cuerpo), encoding="utf-8"
        )
        falla = '<failure message="x"/>' if fallos else ""
        Path(xml.split("=", 1)[1]).write_text(
            '<testsuites><testsuite time="1.0">'
            f'<testcase classname="tests.test_x" name="t" time="0.1">{falla}'
            "</testcase></testsuite></testsuites>",
            encoding="utf-8",
        )
        return _proceso("1 passed")

    return ejecutar


def test_cobertura_suficiente_cumple(cliente, monkeypatch):
    monkeypatch.setattr(calidad_router, "umbral_cobertura", lambda: 80.0)
    monkeypatch.setattr(subprocess, "run", _pytest_falso(95.0, 0))
    datos = cliente.post("/api/calidad/cobertura").json()
    assert datos["cobertura"]["porcentaje"] == 95.0
    assert datos["cobertura"]["archivos"][0]["archivo"] == "rutas/grafo.py"
    assert all(c["ok"] for c in datos["condiciones"])


def test_cobertura_baja_o_pruebas_fallidas_incumplen(cliente, monkeypatch):
    monkeypatch.setattr(calidad_router, "umbral_cobertura", lambda: 80.0)
    monkeypatch.setattr(subprocess, "run", _pytest_falso(10.0, 1))
    datos = cliente.post("/api/calidad/cobertura").json()
    assert datos["pruebas"]["no_aprobadas"] == 1
    assert [c["ok"] for c in datos["condiciones"]] == [False, False]


def test_cobertura_sin_informe_da_error_claro(cliente, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _proceso("", 4, "boom")
    )
    respuesta = cliente.post("/api/calidad/cobertura")
    assert respuesta.status_code == 500
    assert "pytest-cov" in respuesta.json()["detail"]


def test_formato_nuevo_de_ruff_tambien_se_reconoce():
    salida = (
        "rutas/a.py:2:1: unformatted: File would be reformatted\n"
        "1 file would be reformatted\n"
    )
    assert calidad_router.archivos_sin_formato(salida) == ["rutas/a.py"]


def test_formato_real_detecta_un_archivo_mal_formateado(tmp_path):
    """Contra Ruff de verdad: un archivo sin formato se detecta."""
    mal = calidad_router.RAIZ / "_tmp_sin_formato.py"
    mal.write_text("x=1\n", encoding="utf-8")
    try:
        proceso = calidad_router._ruff(
            "format",
            "--check",
            "--output-format",
            "concise",
            "--no-cache",
            str(mal),
        )
    finally:
        mal.unlink()
    assert calidad_router.archivos_sin_formato(
        proceso.stdout + proceso.stderr
    ) == ["_tmp_sin_formato.py"]
