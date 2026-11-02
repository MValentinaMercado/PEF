"""Pruebas de la evaluación del costo y la utilidad del modelo de IA."""

import pytest

from api import analisis_router
from api.estado import estado
from rutas import evaluacion_modelo as ev
from rutas.prediccion import ModeloTiempos, Muestra

PLAN_CHICO = ((100, 2), (200, 3), (400, 4))
PRUEBA_CHICA = ((300, 3),)
COSTO = ev.CostoEntrenamiento(60, 3.0, 6.0, 90.0, 2300)


def _entrenado_sintetico() -> ev.Entrenado:
    """Tiempos exactos t = 0,01 * V (sin ruido): el modelo no se equivoca."""
    entrenamiento = [
        Muestra(n, 3 * n, algoritmo, 0.01 * n)
        for n in (100, 200, 400, 800)
        for algoritmo in ("BFS", "Dijkstra", "A*")
    ]
    prueba = [
        Muestra(n, 3 * n, algoritmo, 0.01 * n)
        for n in (1_000, 2_000)
        for algoritmo in ("BFS", "Dijkstra", "A*")
    ]
    modelo = ModeloTiempos().entrenar(entrenamiento)
    return ev.Entrenado(modelo, entrenamiento, prueba, COSTO)


@pytest.fixture
def modelo_rapido(monkeypatch):
    """Planes chicos para que los endpoints no tarden segundos."""
    estado.entrenado = None
    monkeypatch.setattr(
        analisis_router,
        "medir_entrenamiento",
        lambda: ev.medir_entrenamiento(PLAN_CHICO, PRUEBA_CHICA),
    )
    monkeypatch.setattr(
        analisis_router,
        "comparar_con_medicion_directa",
        lambda e: ev.comparar_con_medicion_directa(e, ((60, 3), (120, 3)), 1),
    )
    yield
    estado.entrenado = None


# --- mediciones -----------------------------------------------------------
def test_el_entrenamiento_registra_cada_parte_del_costo():
    costo = ev.medir_entrenamiento(PLAN_CHICO, PRUEBA_CHICA).costo
    assert costo.muestras == 3 * len(PLAN_CHICO)
    assert costo.recoleccion_s > 0
    assert costo.ajuste_ms > 0
    assert costo.memoria_ajuste_kb > 0
    assert costo.tamano_modelo_bytes > 0


def test_con_datos_exactos_el_error_es_cero_y_vence_a_la_referencia():
    filas = ev.medir_precision(_entrenado_sintetico())
    assert {f.algoritmo for f in filas} == {"A*", "BFS", "Dijkstra"}
    for fila in filas:
        assert fila.error_medio_pct == pytest.approx(0, abs=1e-6)
        assert fila.mae_ms == pytest.approx(0, abs=1e-6)
        assert fila.error_referencia_pct > 50
        assert fila.grafos == 2


def test_la_latencia_se_mide_en_microsegundos_y_memoria():
    latencia = ev.medir_latencia(_entrenado_sintetico().modelo, 100)
    assert latencia.repeticiones == 100
    assert 0 < latencia.prediccion_us < latencia.recomendacion_us
    assert latencia.memoria_kb > 0


def test_la_comparacion_ejecuta_y_predice_en_grafos_nuevos():
    entrenado = ev.medir_entrenamiento(PLAN_CHICO, PRUEBA_CHICA)
    comparacion = ev.comparar_con_medicion_directa(
        entrenado, ((80, 3), (160, 3)), consultas=1
    )
    assert [f.nodos for f in comparacion.filas] == [80, 160]
    assert all(
        f.directo_ms > 0 and f.prediccion_us > 0 for f in comparacion.filas
    )
    assert comparacion.costo_entrenamiento_ms > 0


def test_sin_ahorro_por_consulta_el_entrenamiento_nunca_se_amortiza(
    monkeypatch,
):
    """Si predecir tarda más que ejecutar, no hay nada que amortizar."""
    monkeypatch.setattr(ev, "_mediana_por_llamada_us", lambda *_: 1e9)
    comparacion = ev.comparar_con_medicion_directa(
        _entrenado_sintetico(), ((60, 3),), consultas=1
    )
    assert comparacion.estimaciones_para_amortizar is None
    assert comparacion.filas[0].veces_mas_rapida < 1


# --- conclusiones: mismas entradas, mismo texto, sin IA ---------------------
def test_la_conclusion_de_entrenamiento_distingue_donde_esta_el_costo():
    datos = ev.concluir_entrenamiento(
        ev.CostoEntrenamiento(60, 3.0, 6.0, 9, 9)
    )
    ajuste = ev.concluir_entrenamiento(
        ev.CostoEntrenamiento(60, 0.001, 6.0, 9, 9)
    )
    assert "obtener los datos, no el aprendizaje" in datos
    assert "pesa más de lo esperado" in ajuste


@pytest.mark.parametrize(
    ("error", "esperado"),
    [(5.0, "es buena"), (20.0, "aceptable"), (40.0, "insuficiente")],
)
def test_la_conclusion_de_precision_sigue_los_umbrales(error, esperado):
    fila = ev.FilaPrecision("BFS", 5, 1.0, error, 3.0, 90.0)
    assert esperado in ev.concluir_precision([fila])


def test_la_conclusion_avisa_cuando_el_modelo_no_mejora_la_referencia():
    fila = ev.FilaPrecision("BFS", 5, 1.0, 20.0, 1.0, 10.0)
    assert "no mejora la referencia" in ev.concluir_precision([fila])


def test_la_conclusion_de_latencia_sigue_el_umbral():
    assert "despreciable" in ev.concluir_latencia(
        ev.Latencia(2000, 50, 100, 2)
    )
    assert "es alto" in ev.concluir_latencia(ev.Latencia(2000, 900, 1500, 2))


def _fila(nodos=40_000, error=5.0, veces=100.0):
    return ev.FilaComparacion(nodos, 3 * nodos, 60.0, 62.0, error, 40.0, veces)


@pytest.mark.parametrize(
    ("fila", "amortiza", "esperado"),
    [
        (_fila(error=60.0), 10, "conviene medir directamente"),
        (_fila(), None, "conviene la solución convencional"),
        (
            _fila(),
            ev.UMBRAL_AMORTIZACION + 1,
            "conviene la solución convencional",
        ),
        (_fila(), 50, "la IA se justifica"),
    ],
)
def test_el_veredicto_de_la_comparacion_sigue_las_reglas(
    fila, amortiza, esperado
):
    comparacion = ev.Comparacion("Dijkstra", [fila], 12_000.0, amortiza)
    assert esperado in ev.concluir_comparacion(comparacion)


def test_la_comparacion_nombra_los_tamanos_donde_predecir_pierde():
    filas = [_fila(100, veces=0.5), _fila(40_000)]
    texto = ev.concluir_comparacion(ev.Comparacion("Dijkstra", filas, 1.0, 5))
    assert (
        "En los grafos de 100 nodos ejecutar el algoritmo es más rápido"
        in texto
    )


def test_la_conclusion_es_determinista():
    fila = ev.FilaPrecision("BFS", 5, 1.0, 20.0, 3.0, 90.0)
    primera = ev.concluir_precision([fila])
    segunda = ev.concluir_precision([fila])
    assert primera == segunda


# --- API: cada botón funciona solo -----------------------------------------
def test_cada_medicion_entrena_el_modelo_si_falta(cliente, modelo_rapido):
    datos = cliente.post("/api/analisis/modelo/precision").json()
    assert datos["entrenado_ahora"] is True
    assert datos["conclusion"]
    assert estado.entrenado is not None
    segunda = cliente.post("/api/analisis/modelo/latencia").json()
    assert segunda["entrenado_ahora"] is False
    assert segunda["prediccion_us"] > 0


def test_el_endpoint_de_entrenamiento_siempre_vuelve_a_medir(
    cliente, modelo_rapido
):
    primero = cliente.post("/api/analisis/modelo/entrenamiento").json()
    modelo = estado.entrenado
    cliente.post("/api/analisis/modelo/entrenamiento")
    assert estado.entrenado is not modelo
    assert estado.modelo is estado.entrenado.modelo
    assert primero["muestras"] == 3 * len(PLAN_CHICO)
    assert "Entrenar costó" in primero["conclusion"]


def test_el_endpoint_de_comparacion_devuelve_filas_y_veredicto(
    cliente, modelo_rapido
):
    datos = cliente.post("/api/analisis/modelo/comparacion").json()
    assert [f["nodos"] for f in datos["filas"]] == [60, 120]
    assert "Veredicto" in datos["conclusion"]
    assert datos["entrenado_ahora"] is True
