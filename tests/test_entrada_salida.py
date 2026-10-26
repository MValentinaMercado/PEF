"""Pruebas de la E/S con archivos grandes: buffer, lotes y paralelismo."""

import io
import math
from concurrent.futures import ThreadPoolExecutor

import pytest

from api import analisis_router
from rutas.entrada_salida import (
    ejecutar_entrada_salida,
    escribir_con_buffer,
    escribir_sin_buffer,
    escribir_todo_junto,
    generar_lineas,
    leer_en_lotes,
    leer_linea_a_linea,
    leer_por_lotes,
    leer_todo,
    mapear_acotado,
    procesar_con_hilos,
    procesar_con_procesos,
    procesar_secuencial,
)

LINEAS = 2500  # no es múltiplo del tamaño de lote: hay un último lote corto


@pytest.fixture
def archivo(tmp_path):
    """Archivo de aristas ya escrito."""
    ruta = tmp_path / "aristas.csv"
    escribir_con_buffer(ruta, generar_lineas(LINEAS), 1000)
    return ruta


def test_generador_produce_aristas_validas():
    lineas = list(generar_lineas(500))
    assert len(lineas) == 500
    for linea in lineas:
        origen, destino, peso = linea.rstrip("\n").split(",")
        assert origen != destino and float(peso) > 0


@pytest.mark.parametrize("tamano_buffer", [1, 7, 1000, 5000])
def test_los_modos_de_escritura_producen_el_mismo_archivo(
    tmp_path, tamano_buffer
):
    esperado = "".join(generar_lineas(LINEAS))
    escritas = []
    for nombre, escribir in (
        ("a", lambda r: escribir_sin_buffer(r, generar_lineas(LINEAS))),
        (
            "b",
            lambda r: escribir_con_buffer(
                r, generar_lineas(LINEAS), tamano_buffer
            ),
        ),
        ("c", lambda r: escribir_todo_junto(r, generar_lineas(LINEAS))),
    ):
        ruta = tmp_path / nombre
        escritas.append(escribir(ruta))
        assert ruta.read_text(encoding="utf-8") == esperado
    assert escritas == [LINEAS] * 3


def test_leer_en_lotes_no_pierde_ni_inventa_lineas():
    texto = "".join(generar_lineas(LINEAS))
    lotes = list(leer_en_lotes(io.StringIO(texto), 1000))
    assert [len(lote) for lote in lotes] == [1000, 1000, 500]
    assert all(linea.strip() for lote in lotes for linea in lote)  # sin vacías
    assert "".join(linea for lote in lotes for linea in lote) == texto


def test_los_modos_de_lectura_coinciden(archivo):
    todo = leer_todo(archivo)
    assert todo[0] == LINEAS
    for otro in (leer_linea_a_linea(archivo), leer_por_lotes(archivo, 1000)):
        assert otro[0] == todo[0]
        assert math.isclose(otro[1], todo[1], rel_tol=1e-9)


def test_paralelo_da_el_mismo_resultado_que_secuencial(archivo):
    base = procesar_secuencial(archivo, 400)
    assert base.lineas == LINEAS
    assert sum(base.grados.values()) == 2 * LINEAS  # cada arista toca 2 nodos
    for paralelo in (
        procesar_con_hilos(archivo, 3, 400),
        procesar_con_procesos(archivo, 2, 400),
    ):
        assert paralelo.lineas == base.lineas
        assert paralelo.grados == base.grados
        assert math.isclose(paralelo.suma_pesos, base.suma_pesos, rel_tol=1e-9)


def test_mapear_acotado_conserva_el_orden_y_no_lee_de_mas():
    leidos = []

    def elementos():
        for numero in range(100):
            leidos.append(numero)
            yield numero

    with ThreadPoolExecutor(2) as ejecutor:
        resultados = mapear_acotado(ejecutor, lambda n: n * n, elementos(), 3)
        assert next(resultados) == 0
        assert len(leidos) <= 3  # no se consumió toda la entrada de golpe
        assert list(resultados) == [n * n for n in range(1, 100)]


def test_experimento_completo_con_tamano_reducido():
    r = ejecutar_entrada_salida(20_000, 500, 2)
    assert r.resultados_coinciden
    assert [f.lineas for f in r.escritura + r.lectura] == [20_000] * 6
    assert [f.lineas for f in r.paralelo] == [20_000] * 3
    assert r.escritura[0].aceleracion == r.lectura[0].aceleracion == 1
    assert r.paralelo[0].aceleracion == 1
    # El buffer evita una operación de E/S por línea. Con tan pocas líneas
    # la diferencia es pequeña y el tiempo varía entre equipos: se admite
    # un margen del 50 % para que la prueba no dependa del ruido.
    assert r.escritura[1].tiempo_ms < r.escritura[0].tiempo_ms * 1.5
    # read() carga todo el archivo; línea por línea y por lotes no.
    todo, linea, lotes = (f.memoria_kb for f in r.lectura)
    assert linea < todo / 10 and lotes < todo / 10


def test_endpoint_entrada_salida(cliente, monkeypatch):
    monkeypatch.setattr(
        analisis_router,
        "ejecutar_entrada_salida",
        lambda: ejecutar_entrada_salida(2000, 100, 2),
    )
    datos = cliente.post("/api/analisis/entrada_salida").json()
    assert datos["resultados_coinciden"] is True
    assert len(datos["escritura"]) == len(datos["lectura"]) == 3
    assert [f["modo"] for f in datos["paralelo"]][0] == "Secuencial"
    assert {"modo", "tiempo_ms", "memoria_kb", "lineas", "aceleracion"} == set(
        datos["escritura"][0]
    )
