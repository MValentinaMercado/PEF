"""Pruebas unitarias del Memory Gate."""

from rutas.memory_gate import LIMITE_BYTES, aprobado


def test_aprobado_por_debajo_del_limite() -> None:
    assert aprobado(LIMITE_BYTES - 1)


def test_aprobado_en_el_limite() -> None:
    assert aprobado(LIMITE_BYTES)


def test_rechazado_por_encima_del_limite() -> None:
    assert not aprobado(LIMITE_BYTES + 1)


def test_permite_un_limite_personalizado() -> None:
    assert aprobado(100, limite_bytes=100)
    assert not aprobado(101, limite_bytes=100)