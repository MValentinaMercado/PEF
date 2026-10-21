"""Pruebas de los experimentos de la Ventana 2 (con tamaños reducidos)."""

import pytest

from rutas.benchmark import ejecutar_benchmark
from rutas.concurrencia import ejecutar_concurrencia
from rutas.experimento_cache import ejecutar_experimento_cache
from rutas.perfilado import ejecutar_perfilado


def test_benchmark_devuelve_una_fila_por_algoritmo_y_tamano():
    filas = ejecutar_benchmark(tamanos=(50, 100), consultas=3)
    assert len(filas) == 6
    assert all(f.tiempo_ms > 0 and f.nodos_explorados > 0 for f in filas)


def test_a_estrella_explora_menos_que_dijkstra():
    filas = ejecutar_benchmark(tamanos=(1000,), consultas=10)
    explorados = {f.algoritmo: f.nodos_explorados for f in filas}
    assert explorados["A*"] <= explorados["Dijkstra"]


def test_experimento_de_cache():
    r = ejecutar_experimento_cache(300, 100, 10)
    assert r.aciertos + r.fallos == r.total_consultas
    assert r.fallos <= r.pares_distintos
    assert r.fallo_tras_cambio and r.acierto_al_repetir
    assert r.con_cache[0] < r.sin_cache[0]


def test_concurrencia_procesa_todas_las_consultas():
    filas = ejecutar_concurrencia(300, 40, 2)
    assert [f.consultas_procesadas for f in filas] == [40, 40, 40]
    assert filas[0].aceleracion == 1


def test_perfilado_lista_funciones():
    perfiles = ejecutar_perfilado(300, 3)
    assert set(perfiles) == {"BFS", "Dijkstra", "A*"}
    assert all(0 < len(filas) <= 6 for filas in perfiles.values())


def test_perfilado_guarda_un_prof_por_algoritmo(tmp_path):
    ejecutar_perfilado(300, 3, carpeta_prof=tmp_path)
    assert sorted(a.name for a in tmp_path.glob("*.prof")) == [
        "a_estrella.prof",
        "bfs.prof",
        "dijkstra.prof",
    ]
    assert all(a.stat().st_size > 0 for a in tmp_path.glob("*.prof"))


def test_escalabilidad_compara_con_la_teoria():
    from rutas.benchmark import FilaBenchmark
    from rutas.escalabilidad import comparar_con_teoria, trabajo_teorico

    # Tiempos que siguen exactamente O((V + E) log V): cocientes iguales a 1.
    base = trabajo_teorico("Dijkstra", 1000, 3000)
    medidas = [
        FilaBenchmark(
            n, "Dijkstra", trabajo_teorico("Dijkstra", n, 3 * n) / base, 1, 1
        )
        for n in (1000, 4000, 16000)
    ]
    filas = comparar_con_teoria(
        medidas, {n: 3 * n for n in (1000, 4000, 16000)}
    )
    assert [round(f.razon, 6) for f in filas] == [1.0, 1.0, 1.0]


def test_escalabilidad_detecta_un_algoritmo_que_escala_peor():
    from rutas.benchmark import FilaBenchmark
    from rutas.escalabilidad import comparar_con_teoria

    # BFS cuadrático: el tiempo se cuadruplica al duplicar los nodos.
    medidas = [
        FilaBenchmark(1000, "BFS", 1.0, 1, 500),
        FilaBenchmark(2000, "BFS", 4.0, 1, 1000),
    ]
    filas = comparar_con_teoria(medidas, {1000: 3000, 2000: 6000})
    assert filas[1].razon == pytest.approx(2.0)
    assert filas[1].razon_explorados == pytest.approx(2.0)


def test_endpoint_escalabilidad(cliente, monkeypatch):
    from api import analisis_router
    from rutas import escalabilidad

    def reducido():
        return escalabilidad.ejecutar_escalabilidad(((100, 2), (200, 2)))

    monkeypatch.setattr(analisis_router, "ejecutar_escalabilidad", reducido)
    datos = cliente.post("/api/analisis/escalabilidad").json()
    assert len(datos["filas"]) == 6
    assert [g["nodos"] for g in datos["grafos"]] == [100, 200]
    assert all(
        f["tiempo_ms"] > 0 and f["memoria_kb"] > 0 for f in datos["filas"]
    )
