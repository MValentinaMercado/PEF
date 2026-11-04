"""Pruebas del JavaScript de ``web/js``, ejecutadas con el runner de Node.

La lógica de las ventanas (conclusiones, persistencia y restauración de
resultados) se prueba en ``tests/js`` con ``node:test`` y un DOM simulado,
sin navegador ni dependencias nuevas. Aquí se lanzan desde pytest para que
formen parte de la misma suite; si Node no está instalado, se omiten.
"""

import shutil
import subprocess

import pytest

from rutas.procesos import RAIZ

NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js no está instalado")
def test_el_javascript_de_las_ventanas_pasa_sus_pruebas():
    archivos = sorted((RAIZ / "tests" / "js").glob("*.test.js"))
    assert archivos, "no se encontraron pruebas de JavaScript"
    resultado = subprocess.run(  # noqa: S603 - ejecutable resuelto con which
        [NODE, "--test", *map(str, archivos)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
