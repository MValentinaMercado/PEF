"""Pruebas del Performance Gate (el script que usa el pipeline de CI)."""

from rutas import performance_gate
from rutas.generador import generar_consultas, generar_grafo


def test_aprobado_exige_estar_por_debajo_del_umbral():
    assert performance_gate.aprobado(499.9, 500.0)
    assert not performance_gate.aprobado(500.0, 500.0)
    assert not performance_gate.aprobado(900.0, 500.0)


def test_gate_aprueba_con_un_umbral_holgado(capsys):
    codigo = performance_gate.main(["--nodos", "300", "--umbral-ms", "10000"])
    assert codigo == 0
    assert "Performance Gate PASSED" in capsys.readouterr().out


def test_gate_falla_con_un_umbral_imposible(capsys):
    codigo = performance_gate.main(["--nodos", "300", "--umbral-ms", "0.0001"])
    assert codigo == 1
    assert "Performance Gate FAILED" in capsys.readouterr().out


def test_gate_corta_la_medicion_ante_una_regresion_grave():
    grafo = generar_grafo(200)
    consultas = generar_consultas(grafo, 5)
    tiempos = performance_gate.medir_ms(grafo, consultas, 3, corte_ms=0.0)
    assert len(tiempos) == 1


def test_gate_deja_el_resultado_en_el_resumen_de_github(monkeypatch, tmp_path):
    resumen = tmp_path / "resumen.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(resumen))
    performance_gate.main(["--nodos", "200", "--umbral-ms", "10000"])
    assert "Performance Gate PASSED" in resumen.read_text(encoding="utf-8")


def test_gate_sin_resumen_de_github_no_escribe_nada(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.chdir(tmp_path)
    performance_gate.main(["--nodos", "200", "--umbral-ms", "10000"])
    assert list(tmp_path.iterdir()) == []
