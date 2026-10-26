"""Pruebas de los caminos menos frecuentes: errores, límites y rutas REST.

Los módulos pesados (Sphinx, pytest anidado, SnakeViz, benchmarks) se
sustituyen por dobles para que estas pruebas sean rápidas y deterministas.
"""

import subprocess
from collections import namedtuple
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import (
    analisis_router,
    documentacion,
    pruebas_router,
    visor_perfiles,
)
from api import (
    app as modulo_app,
)
from rutas import concurrencia
from rutas.algoritmos import bfs
from rutas.cache import CacheRutas
from rutas.grafo import Grafo
from rutas.procesos import ruta_relativa

Fila = namedtuple("Fila", ["valor"])


# --------------------------------------------------------------------- grafo
def _grafo_lineal() -> Grafo:
    grafo = Grafo()
    for nombre in "ABC":
        grafo.agregar_nodo(nombre)
    grafo.conectar("A", "B", 1)
    grafo.conectar("B", "C", 1)
    return grafo


def test_eliminar_nodo_quita_sus_conexiones():
    grafo = _grafo_lineal()
    grafo.eliminar_nodo("B")
    assert "B" not in grafo.adyacencia
    assert "B" not in grafo.posiciones
    assert grafo.adyacencia["A"] == {}
    assert grafo.adyacencia["C"] == {}


def test_eliminar_nodo_inexistente_no_falla():
    grafo = _grafo_lineal()
    grafo.eliminar_nodo("Z")
    assert set(grafo.adyacencia) == {"A", "B", "C"}


def test_desbloquear_arista_la_habilita_de_nuevo():
    grafo = _grafo_lineal()
    grafo.establecer_bloqueo("A", "B", True)
    assert grafo.esta_bloqueada("A", "B")
    grafo.establecer_bloqueo("A", "B", False)
    assert not grafo.esta_bloqueada("A", "B")
    assert not grafo.esta_bloqueada("B", "A")


def test_nombre_libre_salta_los_nombres_ocupados():
    grafo = Grafo()
    grafo.agregar_nodo("A")
    grafo.agregar_nodo("C")  # len == 2 sugeriría "C", que ya existe
    assert grafo.nombre_libre() == "D"


# ----------------------------------------------------------------------- BFS
def test_bfs_sin_camino_devuelve_ruta_vacia():
    grafo = Grafo()
    grafo.agregar_nodo("A")
    grafo.agregar_nodo("B")
    resultado = bfs(grafo, "A", "B")
    assert resultado.ruta is None
    assert resultado.distancia == float("inf")


def test_bfs_ignora_vecinos_ya_visitados():
    grafo = _grafo_lineal()
    grafo.conectar("A", "C", 5)  # ciclo: C se alcanza por dos caminos
    resultado = bfs(grafo, "A", "C")
    assert resultado.ruta == ["A", "C"]


# --------------------------------------------------------------------- caché
def test_cache_descarta_la_entrada_mas_antigua_al_llenarse():
    grafo = _grafo_lineal()
    cache = CacheRutas(tamano_maximo=1)
    cache.consultar(grafo, "A", "B")
    cache.consultar(grafo, "A", "C")  # expulsa ("A", "B")
    cache.consultar(grafo, "A", "B")  # vuelve a calcularse
    assert cache.aciertos == 0
    assert cache.fallos == 3


# ----------------------------------------------------------------- rutas REST
def test_renombrar_a_un_nombre_existente_da_409(cliente):
    nombres = [n["nombre"] for n in cliente.get("/api/grafo").json()["nodos"]]
    respuesta = cliente.patch(
        f"/api/nodos/{nombres[0]}", json={"nuevo_nombre": nombres[1]}
    )
    assert respuesta.status_code == 409


@pytest.mark.parametrize(
    ("url", "funcion"),
    [
        ("/api/analisis/benchmark", "ejecutar_benchmark"),
        ("/api/analisis/cache", "ejecutar_experimento_cache"),
        ("/api/analisis/concurrencia", "ejecutar_concurrencia"),
    ],
)
def test_endpoints_de_medicion_serializan_el_resultado(
    cliente, monkeypatch, url, funcion
):
    resultado = Fila(1) if "cache" in url else [Fila(1), Fila(2)]
    monkeypatch.setattr(analisis_router, funcion, lambda: resultado)
    respuesta = cliente.post(url)
    assert respuesta.status_code == 200
    esperado = {"valor": 1} if "cache" in url else [{"valor": 1}, {"valor": 2}]
    assert respuesta.json() == esperado


def test_entrada_salida_serializa_las_tres_tablas(cliente, monkeypatch):
    Resultado = namedtuple("Resultado", ["escritura", "lectura", "paralelo"])
    falso = Resultado([Fila(1)], [Fila(2)], [Fila(3)])
    monkeypatch.setattr(
        analisis_router, "ejecutar_entrada_salida", lambda: falso
    )
    datos = cliente.post("/api/analisis/entrada_salida").json()
    assert datos == {
        "escritura": [{"valor": 1}],
        "lectura": [{"valor": 2}],
        "paralelo": [{"valor": 3}],
    }


def test_perfilado_combina_cpu_y_memoria(cliente, monkeypatch, tmp_path):
    monkeypatch.setattr(visor_perfiles, "CARPETA_PERFILES", tmp_path)
    monkeypatch.setattr(
        analisis_router,
        "ejecutar_perfilado",
        lambda carpeta_prof: {"BFS": [Fila(1)]},
    )
    monkeypatch.setattr(
        analisis_router, "ejecutar_perfilado_memoria", lambda: [Fila(2)]
    )
    datos = cliente.post("/api/analisis/perfilado").json()
    assert datos == {"cpu": {"BFS": [{"valor": 1}]}, "memoria": [{"valor": 2}]}


def test_snakeviz_informa_si_no_puede_iniciar(cliente, tmp_path, monkeypatch):
    for nombre in ("bfs", "dijkstra", "a_estrella"):
        (tmp_path / f"{nombre}.prof").write_bytes(b"")
    monkeypatch.setattr(visor_perfiles, "CARPETA_PERFILES", tmp_path)
    monkeypatch.setattr(
        analisis_router,
        "nombre_archivo_prof",
        lambda nombre: {
            "BFS": "bfs.prof",
            "Dijkstra": "dijkstra.prof",
            "A*": "a_estrella.prof",
        }[nombre],
    )

    def falla(_archivo):
        raise RuntimeError("SnakeViz no pudo iniciarse")

    monkeypatch.setattr(visor_perfiles, "iniciar", falla)
    respuesta = cliente.post("/api/analisis/snakeviz")
    assert respuesta.status_code == 500


# --------------------------------------------------------- pruebas (JUnit XML)
def test_resumir_junit_cuenta_fallas_errores_y_omitidas():
    xml = (
        '<testsuites><testsuite time="2.5">'
        '<testcase classname="tests.test_api" name="a" time="0.1"/>'
        '<testcase classname="tests.test_api" name="b" time="0.2">'
        '<failure message="boom"/></testcase>'
        '<testcase classname="rutas.grafo" name="c" time="0.0">'
        '<error message="x"/></testcase>'
        '<testcase classname="tests.test_rendimiento" name="d" time="0.0">'
        '<skipped message="s"/></testcase>'
        "</testsuite></testsuites>"
    )
    resumen = pruebas_router.resumir_junit(xml)
    assert resumen["total"] == 4
    assert (resumen["aprobadas"], resumen["fallidas"]) == (1, 1)
    assert (resumen["errores"], resumen["omitidas"]) == (1, 1)
    assert resumen["segundos"] == pytest.approx(2.5)


def test_correr_pytest_traduce_el_tiempo_agotado_a_504(monkeypatch):
    def agotado(*_a, **_k):
        raise RuntimeError("pytest tardó demasiado.")

    monkeypatch.setattr(pruebas_router, "ejecutar_modulo", agotado)
    with pytest.raises(pruebas_router.HTTPException) as error:
        pruebas_router.correr_pytest()
    assert error.value.status_code == 504


def test_ejecutar_pruebas_devuelve_el_resumen(cliente, monkeypatch):
    xml = (
        '<testsuites><testsuite time="1.0">'
        '<testcase classname="tests.test_api" name="a" time="0.1"/>'
        "</testsuite></testsuites>"
    )

    def falso(*argumentos, entorno=None):
        ruta = Path(argumentos[0].split("=", 1)[1])
        ruta.write_text(xml, encoding="utf-8")
        return subprocess.CompletedProcess(argumentos, 0, "1 passed", "")

    monkeypatch.setattr(pruebas_router, "correr_pytest", falso)
    datos = cliente.post("/api/pruebas/ejecutar").json()
    assert datos["total"] == 1
    assert datos["salida"] == "1 passed"


def test_ejecutar_pruebas_sin_informe_da_500(cliente, monkeypatch):
    monkeypatch.setattr(
        pruebas_router,
        "correr_pytest",
        lambda *a, **k: subprocess.CompletedProcess(a, 2, "", "sin informe"),
    )
    respuesta = cliente.post("/api/pruebas/ejecutar")
    assert respuesta.status_code == 500
    assert "sin informe" in respuesta.json()["detail"]


# ------------------------------------------------------------- documentación
def _apuntar_documentacion(monkeypatch, carpeta: Path) -> None:
    monkeypatch.setattr(documentacion, "SALIDA", carpeta)


def test_documentacion_no_disponible_sin_html(tmp_path, monkeypatch):
    _apuntar_documentacion(monkeypatch, tmp_path)
    assert not documentacion.disponible()
    assert documentacion.estado_documentacion() == {
        "disponible": False,
        "generada": None,
    }


def test_documentacion_disponible_informa_la_fecha(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    _apuntar_documentacion(monkeypatch, tmp_path)
    estado = documentacion.estado_documentacion()
    assert estado["disponible"] is True
    assert estado["generada"]


def test_construir_lanza_error_si_sphinx_falla(monkeypatch):
    monkeypatch.setattr(
        documentacion.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "salida", "error"),
    )
    with pytest.raises(RuntimeError, match="error"):
        documentacion.construir()


def test_construir_si_falta_solo_construye_una_vez(tmp_path, monkeypatch):
    _apuntar_documentacion(monkeypatch, tmp_path)
    llamadas = []

    def construir_falso():
        llamadas.append(1)
        (tmp_path / "index.html").write_text("x", encoding="utf-8")

    monkeypatch.setattr(documentacion, "construir", construir_falso)
    documentacion.construir_si_falta()
    documentacion.construir_si_falta()
    assert llamadas == [1]


def test_endpoints_de_documentacion(cliente, tmp_path, monkeypatch):
    _apuntar_documentacion(monkeypatch, tmp_path)
    assert (
        cliente.get("/api/documentacion/estado").json()["disponible"] is False
    )

    monkeypatch.setattr(documentacion, "construir", lambda: None)
    assert cliente.post("/api/documentacion/generar").status_code == 200

    def falla():
        raise RuntimeError("no compila")

    monkeypatch.setattr(documentacion, "construir", falla)
    respuesta = cliente.post("/api/documentacion/generar")
    assert respuesta.status_code == 500
    assert "no compila" in respuesta.json()["detail"]


# -------------------------------------------------------------- ciclo de vida
def test_la_app_arranca_aunque_falle_la_documentacion(monkeypatch):
    def falla():
        raise RuntimeError("sin Sphinx")

    monkeypatch.setattr(documentacion, "construir_si_falta", falla)
    with TestClient(modulo_app.app) as cliente:
        assert cliente.get("/").status_code == 200


# ----------------------------------------------------------- visor de perfiles
class _ProcesoFalso:
    def __init__(self, terminado: bool = False, cuelga: bool = False):
        self._terminado = terminado
        self._cuelga = cuelga
        self.terminado_llamado = False
        self.matado = False

    def poll(self):
        return 0 if self._terminado else None

    def terminate(self):
        self.terminado_llamado = True

    def wait(self, timeout=None):
        if self._cuelga:
            raise subprocess.TimeoutExpired("snakeviz", timeout)

    def kill(self):
        self.matado = True


def test_detener_termina_el_proceso(monkeypatch):
    proceso = _ProcesoFalso()
    visor_perfiles._servidor.proceso = proceso
    visor_perfiles.detener()
    assert proceso.terminado_llamado
    assert visor_perfiles._servidor.proceso is None


def test_detener_mata_el_proceso_si_no_responde():
    proceso = _ProcesoFalso(cuelga=True)
    visor_perfiles._servidor.proceso = proceso
    visor_perfiles.detener()
    assert proceso.matado


def test_iniciar_no_relanza_si_ya_esta_escuchando(monkeypatch):
    proceso = _ProcesoFalso()
    visor_perfiles._servidor.proceso = proceso
    monkeypatch.setattr(visor_perfiles, "_escuchando", lambda: True)
    monkeypatch.setattr(
        visor_perfiles.subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("no debía lanzar otro proceso"),
    )
    visor_perfiles.iniciar(Path("x.prof"))
    visor_perfiles._servidor.proceso = None


def test_iniciar_falla_si_el_proceso_muere(monkeypatch):
    visor_perfiles._servidor.proceso = None
    monkeypatch.setattr(visor_perfiles, "_escuchando", lambda: False)
    monkeypatch.setattr(
        visor_perfiles.subprocess,
        "Popen",
        lambda *a, **k: _ProcesoFalso(terminado=True),
    )
    with pytest.raises(RuntimeError, match="SnakeViz"):
        visor_perfiles.iniciar(Path("x.prof"))


def test_iniciar_devuelve_cuando_el_servidor_responde(monkeypatch):
    visor_perfiles._servidor.proceso = None
    respuestas = iter([False, True])
    monkeypatch.setattr(
        visor_perfiles, "_escuchando", lambda: next(respuestas)
    )
    monkeypatch.setattr(visor_perfiles.time, "sleep", lambda _s: None)
    monkeypatch.setattr(
        visor_perfiles.subprocess, "Popen", lambda *a, **k: _ProcesoFalso()
    )
    visor_perfiles.iniciar(Path("x.prof"))
    assert visor_perfiles._servidor.proceso is not None
    visor_perfiles._servidor.proceso = None


# ---------------------------------------------------------------- utilidades
def test_ruta_relativa_fuera_del_proyecto_se_deja_igual():
    assert ruta_relativa("/otra/carpeta/x.py") == "/otra/carpeta/x.py"


def test_grafo_activo_exige_inicializacion(monkeypatch):
    monkeypatch.setattr(concurrencia, "_grafo_trabajo", None)
    with pytest.raises(RuntimeError, match="no fue inicializado"):
        concurrencia._grafo_activo()


def test_trabajador_mide_el_pico_de_memoria(monkeypatch, grafo_ejemplo):
    monkeypatch.setattr(concurrencia, "_grafo_trabajo", None)
    concurrencia._iniciar_trabajador(grafo_ejemplo, medir_memoria=True)
    try:
        assert concurrencia._resolver_midiendo_memoria(("A", "F")) > 0
        assert concurrencia._resolver(("A", "F")) > 0
    finally:
        concurrencia.tracemalloc.stop()
        monkeypatch.setattr(concurrencia, "_grafo_trabajo", None)
