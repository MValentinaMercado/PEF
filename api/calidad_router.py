"""Ventana Calidad: análisis estático con Ruff, cobertura y condiciones.

Son las mismas comprobaciones que ejecuta el pipeline de integración continua
(``.github/workflows/ci.yml``); aquí se ven desde el navegador. Los umbrales
salen de ``pyproject.toml`` para que haya una sola fuente de verdad.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.estado import estado
from api.pruebas_router import correr_pytest, resumir_junit

RAIZ = Path(__file__).resolve().parent.parent
TIEMPO_MAXIMO_S = 300
PATRON_SIN_FORMATO = re.compile(
    r"^(?:Would reformat: (?P<viejo>.+?)"
    r"|(?P<nuevo>.+?):\d+:\d+: unformatted\b.*)\s*$",
    re.MULTILINE,
)

router = APIRouter(prefix="/api/calidad")


def umbral_cobertura() -> float:
    """Cobertura mínima exigida (``fail_under`` de ``pyproject.toml``)."""
    with (RAIZ / "pyproject.toml").open("rb") as archivo:
        config = tomllib.load(archivo)
    return float(config["tool"]["coverage"]["report"]["fail_under"])


def _relativa(ruta: str) -> str:
    """Ruta relativa a la raíz del proyecto, con ``/`` en cualquier sistema.

    >>> _relativa("api/app.py")
    'api/app.py'
    """
    try:
        return Path(ruta).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return Path(ruta).as_posix()


def resumir_ruff(texto_json: str) -> dict:
    """Convierte la salida JSON de ``ruff check`` en un resumen visual.

    >>> r = resumir_ruff('[{"code": "F401", "message": "sin usar",'
    ...                  ' "filename": "x.py",'
    ...                  ' "location": {"row": 3, "column": 1}}]')
    >>> r["total"], r["por_regla"], r["hallazgos"][0]["linea"]
    (1, {'F401': 1}, 3)
    >>> resumir_ruff("[]")["total"]
    0
    """
    hallazgos = [
        {
            "archivo": _relativa(h["filename"]),
            "linea": h["location"]["row"],
            "columna": h["location"]["column"],
            "regla": h["code"] or "",
            "mensaje": h["message"],
        }
        for h in json.loads(texto_json or "[]")
    ]
    hallazgos.sort(key=lambda h: (h["archivo"], h["linea"]))
    por_regla = dict(Counter(h["regla"] for h in hallazgos).most_common())
    return {
        "total": len(hallazgos),
        "por_regla": por_regla,
        "hallazgos": hallazgos,
    }


def archivos_sin_formato(salida: str) -> list[str]:
    """Archivos que ``ruff format --check`` reformaría (formato nuevo/viejo).

    >>> salida = "Would reformat: a.py\\nb.py:2:1: unformatted: x\\n"
    >>> archivos_sin_formato(salida)
    ['a.py', 'b.py']
    """
    return sorted(
        _relativa(m["viejo"] or m["nuevo"])
        for m in PATRON_SIN_FORMATO.finditer(salida)
    )


def condiciones_lint(
    total_hallazgos: int, sin_formato: list[str]
) -> list[dict]:
    """Condiciones de calidad del análisis estático.

    >>> [c["ok"] for c in condiciones_lint(0, [])]
    [True, True]
    >>> [c["ok"] for c in condiciones_lint(2, ["a.py"])]
    [False, False]
    """
    return [
        {
            "nombre": "Ruff: sin hallazgos de calidad",
            "ok": total_hallazgos == 0,
            "detalle": f"{total_hallazgos} hallazgo(s); se exige 0",
        },
        {
            "nombre": "Ruff: formato del código correcto",
            "ok": not sin_formato,
            "detalle": f"{len(sin_formato)} archivo(s) sin formatear; "
            "se exige 0",
        },
    ]


def condiciones_cobertura(
    porcentaje: float, minimo: float, no_aprobadas: int
) -> list[dict]:
    """Condiciones de calidad de las pruebas y su cobertura.

    >>> [c["ok"] for c in condiciones_cobertura(93.0, 80.0, 0)]
    [True, True]
    >>> [c["ok"] for c in condiciones_cobertura(70.0, 80.0, 1)]
    [False, False]
    """
    return [
        {
            "nombre": "Pruebas: todas aprobadas",
            "ok": no_aprobadas == 0,
            "detalle": f"{no_aprobadas} no aprobada(s); se exige 0",
        },
        {
            "nombre": "Cobertura mínima",
            "ok": porcentaje >= minimo,
            "detalle": f"{porcentaje:.1f} % obtenido; se exige {minimo:.0f} %",
        },
    ]


def _ruff(*argumentos: str) -> subprocess.CompletedProcess:
    """Ejecuta Ruff (instalado como módulo de Python) sobre el proyecto."""
    try:
        return subprocess.run(
            [sys.executable, "-m", "ruff", *argumentos],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(504, "Ruff tardó demasiado.") from error


@router.post("/lint")
def ejecutar_lint() -> dict:
    """Corre ``ruff check`` (calidad) y ``ruff format --check`` (formato)."""
    calidad = _ruff("check", ".", "--output-format", "json", "--no-cache")
    if calidad.returncode not in (0, 1):  # 2 = Ruff no pudo ejecutarse
        raise HTTPException(
            500,
            "Ruff no está disponible: "
            f"{(calidad.stderr or calidad.stdout)[-500:]}",
        )
    formato = _ruff(
        "format", "--check", "--output-format", "concise", "--no-cache"
    )
    sin_formato = archivos_sin_formato(formato.stdout + formato.stderr)
    resumen = resumir_ruff(calidad.stdout)
    version = _ruff("--version").stdout.strip()
    return {
        "herramienta": version or "ruff",
        "calidad": resumen,
        "sin_formato": sin_formato,
        "condiciones": condiciones_lint(resumen["total"], sin_formato),
    }


def resumir_cobertura(texto_json: str) -> dict:
    """Resumen por archivo del informe JSON de ``coverage``.

    >>> t = ('{"totals": {"percent_covered": 90.0},'
    ...      ' "files": {"a.py": {"summary": {"num_statements": 10,'
    ...      ' "missing_lines": 1, "percent_covered": 90.0}}}}')
    >>> r = resumir_cobertura(t)
    >>> r["porcentaje"], r["archivos"][0]["faltan"]
    (90.0, 1)
    """
    datos = json.loads(texto_json)
    archivos = [
        {
            "archivo": _relativa(nombre),
            "sentencias": info["summary"]["num_statements"],
            "faltan": info["summary"]["missing_lines"],
            "porcentaje": info["summary"]["percent_covered"],
        }
        for nombre, info in datos["files"].items()
    ]
    archivos.sort(key=lambda a: (a["porcentaje"], a["archivo"]))
    return {
        "porcentaje": datos["totals"]["percent_covered"],
        "archivos": archivos,
    }


def _entorno_cobertura() -> dict[str, str]:
    """Entorno para medir cobertura sin chocar con ``memory_profiler``.

    ``coverage`` usa ``sys.monitoring`` (Python 3.12+) en vez de
    ``sys.settrace``; así no interfiere con el perfilador de memoria.
    """
    return {**os.environ, "COVERAGE_CORE": "sysmon"}


@router.post("/cobertura")
def ejecutar_cobertura() -> dict:
    """Corre ``pytest --cov`` y devuelve cobertura y estado de las pruebas."""
    minimo = umbral_cobertura()
    # Las pruebas de rendimiento miden tiempos: no deben solaparse con
    # otras mediciones de la aplicación.
    with estado.cerrojo_medicion, tempfile.TemporaryDirectory() as carpeta:
        informe_xml = Path(carpeta) / "informe.xml"
        informe_cov = Path(carpeta) / "cobertura.json"
        proceso = correr_pytest(
            "--cov",
            f"--cov-report=json:{informe_cov}",
            f"--junitxml={informe_xml}",
            entorno=_entorno_cobertura(),
        )
        if not (informe_xml.exists() and informe_cov.exists()):
            raise HTTPException(
                500,
                "No se generó el informe (¿está instalado pytest-cov?): "
                + (proceso.stdout + proceso.stderr)[-600:],
            )
        pruebas = resumir_junit(informe_xml.read_text(encoding="utf-8"))
        cobertura = resumir_cobertura(informe_cov.read_text(encoding="utf-8"))
    no_aprobadas = pruebas["fallidas"] + pruebas["errores"]
    return {
        "pruebas": {k: pruebas[k] for k in ("total", "aprobadas", "segundos")}
        | {"no_aprobadas": no_aprobadas},
        "cobertura": cobertura | {"minimo": minimo},
        "condiciones": condiciones_cobertura(
            cobertura["porcentaje"], minimo, no_aprobadas
        ),
        "salida": proceso.stdout[-3000:],
    }
