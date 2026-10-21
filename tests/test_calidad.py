"""Pruebas de la ventana Calidad (SonarQube Cloud) y de su configuración."""

import httpx
import pytest

from api import calidad_router
from rutas.procesos import RAIZ

PUERTA = {
    "projectStatus": {
        "status": "ERROR",
        "conditions": [
            {
                "status": "ERROR",
                "metricKey": "new_coverage",
                "comparator": "LT",
                "errorThreshold": "80",
                "actualValue": "60.5",
            },
            {
                "status": "OK",
                "metricKey": "new_security_rating",
                "comparator": "GT",
                "errorThreshold": "1",
                "actualValue": "1",
            },
        ],
    }
}
MEDIDAS = {
    "component": {
        "measures": [
            {"metric": "bugs", "value": "2"},
            {"metric": "reliability_rating", "value": "3.0"},
        ]
    }
}


def _propiedades() -> dict[str, str]:
    texto = calidad_router.PROPIEDADES.read_text(encoding="utf-8")
    return calidad_router.parsear_propiedades(texto)


def _respuesta(codigo: int, cuerpo: dict | None = None):
    return httpx.Response(
        codigo, json=cuerpo or {}, request=httpx.Request("GET", "http://x")
    )


@pytest.fixture
def sonar_falso(monkeypatch):
    """Reemplaza la API de SonarQube por respuestas fijas."""

    def obtener(ruta, parametros):
        return PUERTA if "qualitygates" in ruta else MEDIDAS

    monkeypatch.setattr(calidad_router, "_obtener", obtener)


def test_pagina_calidad_se_sirve(cliente):
    respuesta = cliente.get("/calidad")
    assert respuesta.status_code == 200
    assert "SonarQube" in respuesta.text


def test_estado_sonar_resume_gate_y_metricas(cliente, sonar_falso):
    datos = cliente.get("/api/calidad/sonar").json()
    assert datos["estado"] == "ERROR"
    assert datos["proyecto"] == _propiedades()["sonar.projectKey"]
    assert datos["organizacion"] == _propiedades()["sonar.organization"]
    assert datos["panel"].endswith(f"id={datos['proyecto']}")
    cobertura, seguridad = datos["condiciones"]
    assert (cobertura["ok"], cobertura["exigencia"]) == (False, "≥ 80")
    assert (seguridad["valor"], seguridad["exigencia"]) == ("A", "≤ A")
    assert {"nombre": "Fiabilidad (calificación)", "valor": "C"} in datos[
        "medidas"
    ]


@pytest.mark.parametrize(
    ("codigo", "mensaje"),
    [(401, "SONAR_TOKEN"), (404, "no conoce el proyecto"), (500, "500")],
)
def test_errores_de_sonar_se_explican(cliente, monkeypatch, codigo, mensaje):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _respuesta(codigo))
    respuesta = cliente.get("/api/calidad/sonar")
    assert respuesta.status_code == 502
    assert mensaje in respuesta.json()["detail"]


def test_sin_conexion_se_informa(cliente, monkeypatch):
    def sin_red(*_, **__):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr(httpx, "get", sin_red)
    respuesta = cliente.get("/api/calidad/sonar")
    assert respuesta.status_code == 502
    assert "No se pudo conectar" in respuesta.json()["detail"]


def test_el_token_se_envia_solo_si_existe(monkeypatch):
    recibidos = []

    def capturar(*_, **kwargs):
        recibidos.append(kwargs["auth"])
        return _respuesta(200, {"ok": True})

    monkeypatch.setattr(httpx, "get", capturar)
    monkeypatch.delenv("SONAR_TOKEN", raising=False)
    calidad_router._obtener("/api/x", {})
    monkeypatch.setenv("SONAR_TOKEN", "secreto")
    calidad_router._obtener("/api/x", {})
    assert recibidos == [None, ("secreto", "")]


def test_servidor_configurable_por_variable(monkeypatch):
    monkeypatch.setenv("SONAR_URL", "https://otro.example/")
    assert calidad_router._servidor() == "https://otro.example"


def test_configuracion_de_sonar_esta_completa():
    propiedades = _propiedades()
    for clave in ("sonar.organization", "sonar.projectKey", "sonar.sources"):
        assert propiedades[clave]
    for carpeta in propiedades["sonar.sources"].split(","):
        assert (RAIZ / carpeta).exists(), carpeta


def test_el_pipeline_genera_el_informe_que_sonar_espera():
    flujo = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    informe = _propiedades()["sonar.python.coverage.reportPaths"]
    assert "--cov-report=xml" in flujo
    assert informe == "coverage.xml"
    assert "SonarSource/sonarqube-scan-action" in flujo
    assert "sonar.qualitygate.wait=true" in flujo
    assert "secrets.SONAR_TOKEN" in flujo
