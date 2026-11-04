"""Pruebas del estado del pipeline de CI (GitHub Actions)."""

import httpx
import pytest

from api import ci_github

CORRIDA = {
    "id": 99,
    "run_number": 42,
    "status": "completed",
    "conclusion": "success",
    "head_sha": "0123456789abcdef",
    "event": "push",
    "display_title": "Optimiza Dijkstra",
    "run_started_at": "2026-10-01T10:00:00Z",
    "updated_at": "2026-10-01T10:03:00Z",
    "html_url": "https://github.com/ana/rutas/actions/runs/99",
}
TRABAJOS = [
    {
        "name": "Pruebas y cobertura",
        "status": "completed",
        "conclusion": "success",
        "started_at": "2026-10-01T10:00:00Z",
        "completed_at": "2026-10-01T10:02:00Z",
        "html_url": "https://github.com/ana/rutas/actions/runs/99/job/1",
        "steps": [{"name": "pytest", "conclusion": "success"}],
    }
]


def _respuesta(codigo: int, cuerpo: dict | None = None):
    return httpx.Response(
        codigo, json=cuerpo or {}, request=httpx.Request("GET", "http://x")
    )


@pytest.fixture
def github_falso(monkeypatch):
    """Reemplaza la API de GitHub por respuestas fijas."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "ana/rutas")
    pedidos = []

    def obtener(ruta, parametros):
        pedidos.append(ruta)
        if ruta.endswith("/jobs"):
            return {"jobs": TRABAJOS}
        return {"workflow_runs": [CORRIDA, CORRIDA | {"run_number": 41}]}

    monkeypatch.setattr(ci_github, "_obtener", obtener)
    return pedidos


def test_el_estado_del_ci_resume_corrida_etapas_e_historial(
    cliente, github_falso
):
    datos = cliente.get("/api/calidad/ci").json()
    assert datos["repositorio"] == "ana/rutas"
    assert datos["ultima"]["estado"] == "aprobado"
    assert datos["ultima"]["commit"] == "0123456"
    assert datos["ultima"]["segundos"] == 180
    assert [c["numero"] for c in datos["historial"]] == [42, 41]
    assert datos["etapas"][0]["segundos"] == 120
    assert datos["etapas"][0]["controles"][0] == {
        "nombre": "pytest",
        "estado": "aprobado",
    }
    assert "aprobada" in datos["conclusion"]
    assert datos["panel"].endswith("/actions/workflows/ci.yml")
    # La segunda consulta es de los jobs de la corrida más reciente.
    assert github_falso[-1] == "/repos/ana/rutas/actions/runs/99/jobs"


def test_una_corrida_rechazada_explica_que_paso_fallo(cliente, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "ana/rutas")
    fallida = CORRIDA | {"conclusion": "failure"}
    trabajo = TRABAJOS[0] | {
        "conclusion": "failure",
        "steps": [{"name": "Bandit", "conclusion": "failure"}],
    }
    monkeypatch.setattr(
        ci_github,
        "_obtener",
        lambda ruta, _: (
            {"jobs": [trabajo]}
            if ruta.endswith("/jobs")
            else {"workflow_runs": [fallida]}
        ),
    )
    datos = cliente.get("/api/calidad/ci").json()
    assert datos["ultima"]["estado"] == "rechazado"
    assert datos["etapas"][0]["paso_fallido"] == "Bandit"
    assert "rechazado" in datos["conclusion"]
    assert (
        "Pruebas y cobertura (rechazado, paso «Bandit»" in datos["conclusion"]
    )


def test_una_corrida_en_curso_se_indica(cliente, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "ana/rutas")
    en_curso = CORRIDA | {"status": "in_progress", "conclusion": None}
    monkeypatch.setattr(
        ci_github,
        "_obtener",
        lambda ruta, _: (
            {"jobs": []}
            if ruta.endswith("/jobs")
            else {"workflow_runs": [en_curso]}
        ),
    )
    datos = cliente.get("/api/calidad/ci").json()
    assert datos["ultima"]["estado"] == "en curso"
    assert "se está ejecutando" in datos["conclusion"]


def test_sin_corridas_se_informa(cliente, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "ana/rutas")
    monkeypatch.setattr(
        ci_github, "_obtener", lambda *_: {"workflow_runs": []}
    )
    respuesta = cliente.get("/api/calidad/ci")
    assert respuesta.status_code == 404
    assert "todavía no se ejecutó" in respuesta.json()["detail"]


# --- repositorio -------------------------------------------------------------
def test_el_repositorio_sale_de_la_variable(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", " ana/rutas ")
    assert ci_github.repositorio() == "ana/rutas"


def test_el_repositorio_sale_del_remoto_origin(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text(
        '[core]\n\tbare = false\n[remote "origin"]\n'
        "\turl = git@github.com:ana/rutas.git\n\tfetch = +refs/*\n"
        '[branch "main"]\n\tremote = origin\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(ci_github, "RAIZ", tmp_path)
    assert ci_github.repositorio() == "ana/rutas"


@pytest.mark.parametrize(
    "config", [None, '[remote "origin"]\n\turl = https://gitlab.com/a/b\n']
)
def test_sin_repositorio_se_explica_que_definir(
    cliente, monkeypatch, tmp_path, config
):
    if config is not None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text(config, encoding="utf-8")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(ci_github, "RAIZ", tmp_path)
    respuesta = cliente.get("/api/calidad/ci")
    assert respuesta.status_code == 409
    assert "GITHUB_REPOSITORY" in respuesta.json()["detail"]


# --- API de GitHub -----------------------------------------------------------
@pytest.mark.parametrize(
    ("codigo", "mensaje"),
    [
        (401, "GITHUB_TOKEN"),
        (403, "límite"),
        (404, "no encontró"),
        (500, "500"),
    ],
)
def test_los_errores_de_github_se_explican(
    cliente, monkeypatch, codigo, mensaje
):
    monkeypatch.setenv("GITHUB_REPOSITORY", "ana/rutas")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _respuesta(codigo))
    respuesta = cliente.get("/api/calidad/ci")
    assert respuesta.status_code == 502
    assert mensaje in respuesta.json()["detail"]


def test_sin_conexion_con_github_se_informa(cliente, monkeypatch):
    def sin_red(*_, **__):
        raise httpx.ConnectError("sin red")

    monkeypatch.setenv("GITHUB_REPOSITORY", "ana/rutas")
    monkeypatch.setattr(httpx, "get", sin_red)
    respuesta = cliente.get("/api/calidad/ci")
    assert respuesta.status_code == 502
    assert "No se pudo conectar con GitHub" in respuesta.json()["detail"]


def test_el_token_se_envia_solo_si_existe(monkeypatch):
    cabeceras = []

    def capturar(*_, **kwargs):
        cabeceras.append(kwargs["headers"])
        return _respuesta(200, {"ok": True})

    monkeypatch.setattr(httpx, "get", capturar)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    ci_github._obtener("/repos/x", {})
    monkeypatch.setenv("GITHUB_TOKEN", "secreto")
    ci_github._obtener("/repos/x", {})
    assert "Authorization" not in cabeceras[0]
    assert cabeceras[1]["Authorization"] == "Bearer secreto"


def test_solo_se_entregan_enlaces_https():
    assert ci_github._enlace("javascript:alert(1)") is None
    assert ci_github._enlace(None) is None
    assert (
        ci_github._enlace("https://github.com/a/b") == "https://github.com/a/b"
    )


def test_el_estado_sin_resultado_conocido():
    assert ci_github.estado_legible("completed", None) == "sin resultado"
    assert ci_github.estado_legible("completed", "neutral") == "sin resultado"


def test_el_pipeline_incluye_los_jobs_que_la_ventana_muestra():
    """La ventana lista los jobs de ci.yml: el flujo debe existir."""
    flujo = (
        ci_github.RAIZ / ".github" / "workflows" / ci_github.FLUJO
    ).read_text(encoding="utf-8")
    assert "name: Resultado final" in flujo
    assert f"branches: [{ci_github.RAMA}]" in flujo


def test_el_resumen_del_historial_incluye_canceladas_y_etapas_omitidas():
    ultima = {"numero": 50, "estado": "rechazado"}
    etapas = [
        {"nombre": "Pruebas", "estado": "rechazado", "paso_fallido": "pytest"},
        {"nombre": "Rendimiento", "estado": "omitido", "paso_fallido": None},
    ]
    historial = [
        ultima,
        {"numero": 49, "estado": "cancelado"},
        {"numero": 48, "estado": "aprobado"},
    ]
    conclusion = ci_github.concluir_ci(ultima, etapas, historial)
    assert "Pruebas (rechazado, paso «pytest»)" in conclusion
    assert "Rendimiento (omitido)" in conclusion
    assert "1 canceladas" in conclusion
