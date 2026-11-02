"""Pruebas del Memory Gate (el script que usa el pipeline de CI)."""

from rutas import memory_gate
from rutas.generador import generar_consultas, generar_grafo


def test_dentro_del_limite_acepta_el_valor_exacto():
    assert memory_gate.dentro_del_limite(31.9, 32.0)
    assert memory_gate.dentro_del_limite(32.0, 32.0)
    assert not memory_gate.dentro_del_limite(32.1, 32.0)


def test_el_pico_es_el_mayor_de_las_consultas_y_se_repite():
    grafo = generar_grafo(300)
    consultas = generar_consultas(grafo, 3)
    primero = memory_gate.pico_mib(grafo, consultas)
    assert primero > 0
    # tracemalloc cuenta asignaciones de Python: no depende de la máquina.
    assert memory_gate.pico_mib(grafo, consultas) == primero


def test_gate_aprueba_con_un_limite_holgado(capsys):
    codigo = memory_gate.main(["--nodos", "300", "--limite-mib", "1000"])
    assert codigo == 0
    assert "Memory Gate PASSED" in capsys.readouterr().out


def test_gate_falla_con_un_limite_imposible(capsys):
    codigo = memory_gate.main(["--nodos", "300", "--limite-mib", "0.0001"])
    assert codigo == 1
    assert "Memory Gate FAILED" in capsys.readouterr().out


def test_gate_deja_el_resultado_en_el_resumen_de_github(monkeypatch, tmp_path):
    resumen = tmp_path / "resumen.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(resumen))
    memory_gate.main(["--nodos", "200", "--limite-mib", "1000"])
    contenido = resumen.read_text(encoding="utf-8")
    assert "### Memory Gate" in contenido
    assert "Memory Gate PASSED" in contenido
