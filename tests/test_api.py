"""Pruebas de integración de la API FastAPI (editor y rutas)."""

import pytest


def rutas(cliente, origen="A", destino="F", algoritmos=None):
    cuerpo = {"origen": origen, "destino": destino, "repeticiones": 2}
    if algoritmos:
        cuerpo["algoritmos"] = algoritmos
    return cliente.post("/api/rutas", json=cuerpo)


def test_paginas_html(cliente):
    for url in (
        "/",
        "/analisis",
        "/optimizacion",
        "/pruebas",
        "/documentacion",
    ):
        respuesta = cliente.get(url)
        assert respuesta.status_code == 200
        assert "<html" in respuesta.text


def test_grafo_inicial(cliente):
    datos = cliente.get("/api/grafo").json()
    assert len(datos["nodos"]) == 6 and len(datos["aristas"]) == 9


def test_bfs_y_dijkstra_difieren(cliente):
    filas = {f["algoritmo"]: f for f in rutas(cliente).json()}
    assert filas["BFS"]["ruta"] == ["A", "B", "D", "F"]
    assert filas["Dijkstra"]["distancia"] == 520
    assert filas["A*"]["distancia"] == filas["Dijkstra"]["distancia"]
    assert filas["BFS"]["distancia"] > filas["Dijkstra"]["distancia"]
    assert all(
        f["tiempo_ms"] > 0 and f["memoria_kb"] > 0 for f in filas.values()
    )


def test_crud_de_nodos(cliente):
    nuevo = cliente.post("/api/nodos", json={"x": 10, "y": 20}).json()
    assert "G" in [n["nombre"] for n in nuevo["nodos"]]
    movido = cliente.patch("/api/nodos/G", json={"x": 99}).json()
    assert {"nombre": "G", "x": 99, "y": 20} in movido["nodos"]
    renombrado = cliente.patch("/api/nodos/G", json={"nuevo_nombre": "Z"})
    assert "Z" in [n["nombre"] for n in renombrado.json()["nodos"]]
    borrado = cliente.delete("/api/nodos/Z").json()
    assert len(borrado["nodos"]) == 6


def test_conectar_editar_y_eliminar_arista(cliente):
    cliente.post("/api/nodos", json={"nombre": "X", "x": 1, "y": 1})
    cliente.put("/api/aristas", json={"a": "A", "b": "X", "peso": 7})
    cliente.put("/api/aristas", json={"a": "A", "b": "X", "peso": 9})
    aristas = cliente.get("/api/grafo").json()["aristas"]
    assert [e["peso"] for e in aristas if "X" in (e["a"], e["b"])] == [9]
    assert cliente.delete("/api/aristas/A/X").status_code == 200
    assert cliente.delete("/api/aristas/A/X").status_code == 404


def test_bloqueo_cambia_la_ruta(cliente):
    cliente.patch(
        "/api/aristas/bloqueo", json={"a": "B", "b": "D", "bloqueada": True}
    )
    fila = rutas(cliente, algoritmos=["BFS"]).json()[0]
    assert fila["ruta"] != ["A", "B", "D", "F"]
    cliente.patch(
        "/api/aristas/bloqueo", json={"a": "D", "b": "F", "bloqueada": True}
    )
    cliente.patch(
        "/api/aristas/bloqueo", json={"a": "E", "b": "F", "bloqueada": True}
    )
    fila = rutas(cliente, algoritmos=["Dijkstra"]).json()[0]
    assert fila["ruta"] is None and fila["distancia"] is None


@pytest.mark.parametrize(
    "metodo, url, cuerpo, codigo",
    [
        ("patch", "/api/nodos/ZZ", {"x": 1}, 404),
        ("post", "/api/nodos", {"nombre": "A", "x": 1, "y": 1}, 409),
        ("post", "/api/nodos", {"nombre": "a b", "x": 1, "y": 1}, 422),
        ("put", "/api/aristas", {"a": "A", "b": "B", "peso": 0}, 422),
        ("put", "/api/aristas", {"a": "A", "b": "A", "peso": 1}, 422),
        ("put", "/api/aristas", {"a": "A", "b": "Q", "peso": 1}, 404),
        ("post", "/api/rutas", {"origen": "A", "destino": "A"}, 422),
        ("post", "/api/rutas", {"origen": "A", "destino": "Q"}, 404),
        (
            "post",
            "/api/rutas",
            {"origen": "A", "destino": "F", "algoritmos": ["DFS"]},
            422,
        ),
    ],
)
def test_errores_de_validacion(cliente, metodo, url, cuerpo, codigo):
    assert getattr(cliente, metodo)(url, json=cuerpo).status_code == codigo


def test_limpiar_y_ejemplo(cliente):
    assert cliente.delete("/api/grafo").json()["nodos"] == []
    assert len(cliente.post("/api/grafo/ejemplo").json()["nodos"]) == 6


def test_informacion_de_algoritmos(cliente):
    filas = cliente.get("/api/informacion").json()
    assert [f["algoritmo"] for f in filas] == ["BFS", "Dijkstra", "A*"]


def test_snakeviz_pide_perfilar_primero(cliente, tmp_path, monkeypatch):
    from api import visor_perfiles

    monkeypatch.setattr(visor_perfiles, "CARPETA_PERFILES", tmp_path)
    respuesta = cliente.post("/api/analisis/snakeviz")
    assert respuesta.status_code == 409


def test_snakeviz_devuelve_una_url_por_algoritmo(
    cliente, tmp_path, monkeypatch
):
    from api import visor_perfiles
    from rutas.perfilado import ejecutar_perfilado

    monkeypatch.setattr(visor_perfiles, "CARPETA_PERFILES", tmp_path)
    ejecutar_perfilado(200, 2, carpeta_prof=tmp_path)
    try:
        respuesta = cliente.post("/api/analisis/snakeviz")
        assert respuesta.status_code == 200
        urls = respuesta.json()
        assert set(urls) == {"BFS", "Dijkstra", "A*"}
        assert all("/snakeviz/" in url for url in urls.values())
    finally:
        visor_perfiles.detener()
