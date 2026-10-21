"""Ventana Pruebas: ejecuta la suite y devuelve los resultados."""

import subprocess
import tempfile
from pathlib import Path

from defusedxml import ElementTree as ET
from fastapi import APIRouter, HTTPException

from api.estado import estado
from rutas.procesos import ejecutar_modulo

RAIZ = Path(__file__).resolve().parent.parent
TIEMPO_MAXIMO_S = 300

router = APIRouter(prefix="/api/pruebas")


def clasificar(clase: str) -> str:
    """Tipo de prueba según el nombre de clase que informa pytest.

    >>> clasificar("tests.test_algoritmos.PruebasAlgoritmos")
    'unittest'
    >>> clasificar("tests.test_api")
    'pytest'
    >>> clasificar("tests.test_rendimiento")
    'timeit'
    >>> clasificar("rutas.grafo")
    'doctest'
    """
    if clase.startswith("tests.test_rendimiento"):
        return "timeit"
    if clase.startswith("tests."):
        partes = clase.split(".")
        return "unittest" if len(partes) > 2 else "pytest"
    return "doctest"


def resumir_junit(texto_xml: str) -> dict:
    """Convierte el XML JUnit de pytest en un resumen para la interfaz.

    >>> xml = ('<testsuites><testsuite tests="1" time="0.5">'
    ...        '<testcase classname="tests.test_api" name="test_x" '
    ...        'time="0.1"/></testsuite></testsuites>')
    >>> r = resumir_junit(xml)
    >>> r["total"], r["aprobadas"], r["pruebas"][0]["tipo"]
    (1, 1, 'pytest')
    """
    raiz = ET.fromstring(texto_xml)
    pruebas: list[dict] = []
    for caso in raiz.iter("testcase"):
        resultado, detalle = "ok", ""
        for etiqueta, nombre in (
            ("failure", "falló"),
            ("error", "error"),
            ("skipped", "omitida"),
        ):
            hallado = caso.find(etiqueta)
            if hallado is not None:
                resultado = nombre
                detalle = (hallado.get("message") or "")[:500]
        clase = caso.get("classname", "")
        pruebas.append(
            {
                "tipo": clasificar(clase),
                "grupo": clase,
                "nombre": caso.get("name", ""),
                "resultado": resultado,
                "segundos": float(caso.get("time", 0)),
                "detalle": detalle,
            }
        )
    cuenta = {
        r: sum(1 for p in pruebas if p["resultado"] == r)
        for r in ("ok", "falló", "error", "omitida")
    }
    suites = list(raiz.iter("testsuite"))
    return {
        "total": len(pruebas),
        "aprobadas": cuenta["ok"],
        "fallidas": cuenta["falló"],
        "errores": cuenta["error"],
        "omitidas": cuenta["omitida"],
        "segundos": sum(float(s.get("time", 0)) for s in suites),
        "pruebas": pruebas,
    }


def correr_pytest(
    *argumentos: str, entorno: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """Corre ``pytest -q`` con los argumentos dados.

    pytest devuelve un código distinto de 0 si hay pruebas fallidas, por eso
    no se revisa: quien llama lee los informes que le pidió a pytest. Falla
    con 504 si tarda más que ``TIEMPO_MAXIMO_S``.
    """
    try:
        return ejecutar_modulo(
            "pytest",
            "-q",
            *argumentos,
            tiempo=TIEMPO_MAXIMO_S,
            entorno=entorno,
        )
    except RuntimeError as error:
        raise HTTPException(504, "Las pruebas tardaron demasiado.") from error


@router.post("/ejecutar")
def ejecutar_pruebas() -> dict:
    """Corre ``pytest`` (unittest + pytest + doctest + timeit)."""
    # Las pruebas de rendimiento miden tiempos: no deben solaparse con
    # otras mediciones de la aplicación.
    with estado.cerrojo_medicion, tempfile.TemporaryDirectory() as carpeta:
        informe = Path(carpeta) / "informe.xml"
        proceso = correr_pytest(f"--junitxml={informe}")
        if not informe.exists():
            raise HTTPException(500, (proceso.stdout + proceso.stderr)[-800:])
        resumen = resumir_junit(informe.read_text(encoding="utf-8"))
    resumen["salida"] = proceso.stdout[-3000:]
    return resumen
