"""Ventana Optimización: herramientas que detectan código redundante.

Cada herramienta mira el código desde un ángulo distinto:

* **Ruff**: imports y variables sin usar, código comentado, simplificaciones.
* **Vulture**: funciones, clases y variables que nadie usa (código muerto).
* **Pylint**: bloques de código repetidos en varios archivos.
* **Radon**: complejidad ciclomática e índice de mantenibilidad.
* **coverage**: líneas que ninguna prueba ejecuta (candidatas a código muerto).

Todas se invocan como módulo de Python (``python -m herramienta``), sin
``shell``, y devuelven el mismo formato JSON para que la página las muestre
con un único código.
"""

import json
import re
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException

from api.estado import estado
from api.pruebas_router import correr_pytest
from rutas.procesos import ejecutar_modulo, entorno_cobertura, ruta_relativa

OBJETIVOS = ("rutas", "api", "main.py")
PRUEBA_LENTA = (
    "tests/test_perfilado_lineas.py::test_scalene_real_perfila_el_proyecto"
)
REGLAS_RUFF = "F401,F811,F841,ERA001,SIM,C4,PIE"
RANGO_MAXIMO_ACEPTADO = "B"  # complejidad ciclomática de 6 a 10
PATRON_VULTURE = re.compile(
    r"^(?P<archivo>.+?):(?P<linea>\d+): (?P<mensaje>.+?)"
    r" \((?P<confianza>\d+)% confidence\)$",
    re.MULTILINE,
)
PATRON_BLOQUE = re.compile(
    r"==(?P<modulo>[\w.]+):\[(?P<inicio>\d+):(?P<fin>\d+)\]"
)

router = APIRouter(prefix="/api/optimizacion")


def agrupar_lineas(lineas: list[int]) -> list[tuple[int, int]]:
    """Agrupa números de línea consecutivos en tramos ``(inicio, fin)``.

    >>> agrupar_lineas([3, 4, 5, 9, 12, 13])
    [(3, 5), (9, 9), (12, 13)]
    >>> agrupar_lineas([])
    []
    """
    tramos: list[tuple[int, int]] = []
    for linea in sorted(lineas):
        if tramos and linea == tramos[-1][1] + 1:
            tramos[-1] = (tramos[-1][0], linea)
        else:
            tramos.append((linea, linea))
    return tramos


def hallazgos_ruff(texto_json: str) -> list[dict]:
    """Filas para la tabla a partir de la salida JSON de ``ruff check``.

    >>> texto = ('[{"code": "F401", "message": "sin usar", "filename": "x.py",'
    ...          ' "location": {"row": 3, "column": 1}}]')
    >>> [(h["linea"], h["regla"]) for h in hallazgos_ruff(texto)]
    [(3, 'F401')]
    >>> hallazgos_ruff("[]")
    []
    """
    hallazgos = [
        {
            "archivo": ruta_relativa(h["filename"]),
            "linea": h["location"]["row"],
            "regla": h["code"] or "",
            "mensaje": h["message"],
        }
        for h in json.loads(texto_json or "[]")
    ]
    hallazgos.sort(key=lambda h: (h["archivo"], h["linea"]))
    return hallazgos


def hallazgos_vulture(salida: str) -> list[dict]:
    """Convierte la salida de texto de Vulture en filas para la tabla.

    >>> texto = "rutas/a.py:7: unused function 'f' (60% confidence)\\n"
    >>> h = hallazgos_vulture(texto)
    >>> h[0]["linea"], h[0]["regla"], h[0]["mensaje"]
    (7, '60 %', "unused function 'f'")
    >>> hallazgos_vulture("")
    []
    """
    return [
        {
            "archivo": ruta_relativa(m["archivo"]),
            "linea": int(m["linea"]),
            "regla": f"{m['confianza']} %",
            "mensaje": m["mensaje"],
        }
        for m in PATRON_VULTURE.finditer(salida)
    ]


def hallazgos_pylint(texto_json: str) -> list[dict]:
    """Una fila por cada tramo repetido que informa ``duplicate-code``.

    >>> mensaje = "Similar lines in 2 files\\n==a.x:[1:5]\\n==b.y:[7:11]\\n"
    >>> texto = json.dumps(
    ...     {"messages": [{"symbol": "duplicate-code", "message": mensaje}]}
    ... )
    >>> [(h["archivo"], h["linea"]) for h in hallazgos_pylint(texto)]
    [('a/x.py', 1), ('b/y.py', 7)]
    """
    hallazgos = []
    for aviso in json.loads(texto_json)["messages"]:
        if aviso["symbol"] != "duplicate-code":
            continue
        tramos = [
            (
                m["modulo"].replace(".", "/") + ".py",
                int(m["inicio"]),
                int(m["fin"]),
            )
            for m in PATRON_BLOQUE.finditer(aviso["message"])
        ]
        for archivo, inicio, fin in tramos:
            otros = ", ".join(f"{a}:{i}" for a, i, _ in tramos if a != archivo)
            hallazgos.append(
                {
                    "archivo": archivo,
                    "linea": inicio,
                    "regla": "R0801",
                    "mensaje": f"bloque de líneas {inicio}-{fin}; "
                    f"también en {otros or 'el mismo archivo'}",
                }
            )
    return hallazgos


def resumir_radon(texto_cc: str, texto_mi: str) -> dict:
    """Resume complejidad ciclomática (``cc``) y mantenibilidad (``mi``).

    >>> cc = json.dumps({"a.py": [
    ...     {"name": "f", "classname": None, "rank": "A",
    ...      "complexity": 2, "lineno": 1},
    ...     {"name": "g", "classname": "K", "rank": "C",
    ...      "complexity": 12, "lineno": 9}]})
    >>> mi = json.dumps({"a.py": {"mi": 70.5, "rank": "A"}})
    >>> r = resumir_radon(cc, mi)
    >>> r["excesivas"], r["promedio"], r["mas_complejas"][0]["mensaje"]
    (1, 7.0, 'K.g')
    >>> r["mantenibilidad"]["archivo"], r["mantenibilidad"]["valor"]
    ('a.py', 70.5)
    """
    funciones = [
        {
            "archivo": ruta_relativa(archivo),
            "linea": bloque["lineno"],
            "regla": f"{bloque['rank']} ({bloque['complexity']})",
            "mensaje": ".".join(
                filter(None, (bloque.get("classname"), bloque["name"]))
            ),
            "rango": bloque["rank"],
            "complejidad": bloque["complexity"],
        }
        for archivo, bloques in json.loads(texto_cc).items()
        if isinstance(bloques, list)
        for bloque in bloques
    ]
    funciones.sort(key=lambda f: -f["complejidad"])
    indices = {
        ruta_relativa(archivo): datos["mi"]
        for archivo, datos in json.loads(texto_mi).items()
        if isinstance(datos, dict) and "mi" in datos
    }
    peor_archivo = min(indices, key=lambda a: indices[a], default="")
    return {
        "funciones": len(funciones),
        "promedio": round(
            sum(f["complejidad"] for f in funciones) / (len(funciones) or 1),
            2,
        ),
        "excesivas": sum(
            f["rango"] > RANGO_MAXIMO_ACEPTADO for f in funciones
        ),
        "mas_complejas": funciones[:5],
        "mantenibilidad": {
            "archivo": peor_archivo,
            "valor": round(indices.get(peor_archivo, 0.0), 1),
        },
    }


def resumir_lineas_sin_ejecutar(texto_json: str) -> dict:
    """Tramos de líneas que ninguna prueba ejecuta, según ``coverage``.

    >>> t = json.dumps({"totals": {"missing_lines": 3}, "files": {
    ...     "a.py": {"missing_lines": [4, 5, 9]}, "b.py": {"missing_lines": []}
    ... }})
    >>> r = resumir_lineas_sin_ejecutar(t)
    >>> r["total"], [(f["archivo"], f["mensaje"]) for f in r["filas"]]
    (3, [('a.py', 'líneas 4-5'), ('a.py', 'línea 9')])
    """
    datos = json.loads(texto_json)
    filas = [
        {
            "archivo": ruta_relativa(archivo),
            "linea": inicio,
            "regla": "sin ejecutar",
            "mensaje": f"líneas {inicio}-{fin}"
            if fin > inicio
            else f"línea {inicio}",
        }
        for archivo, info in datos["files"].items()
        for inicio, fin in agrupar_lineas(info["missing_lines"])
    ]
    return {"total": datos["totals"]["missing_lines"], "filas": filas}


def _ejecutar(
    modulo: str,
    *argumentos: str,
    tiempo: int = 120,
    entorno: dict[str, str] | None = None,
    codigos_validos: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess:
    """Corre ``python -m modulo`` en la raíz del proyecto.

    Falla con 504 si tarda demasiado y con 500 si la herramienta no está
    instalada o termina con un código inesperado.
    """
    try:
        proceso = ejecutar_modulo(
            modulo, *argumentos, tiempo=tiempo, entorno=entorno
        )
    except RuntimeError as error:
        raise HTTPException(504, str(error)) from error
    if (
        proceso.returncode not in codigos_validos
        or "No module named" in proceso.stderr
    ):
        raise HTTPException(
            500,
            f"{modulo} no se pudo ejecutar: "
            f"{(proceso.stderr or proceso.stdout)[-500:]}",
        )
    return proceso


def _respuesta(
    nombre: str,
    criterio: str,
    filas: list[dict],
    *,
    cumple: bool | None,
    fichas: list[dict] | None = None,
    total: int | None = None,
) -> dict:
    """Formato común: la página muestra cualquier herramienta igual."""
    return {
        "herramienta": f"{nombre} {version(nombre.lower())}",
        "criterio": criterio,
        "cumple": cumple,
        "total": len(filas) if total is None else total,
        "filas": filas,
        "fichas": fichas or [],
    }


def _ruff() -> dict:
    proceso = _ejecutar(
        "ruff",
        "check",
        ".",
        "--select",
        REGLAS_RUFF,
        "--output-format",
        "json",
        "--no-cache",
        codigos_validos=(0, 1),
    )
    filas = hallazgos_ruff(proceso.stdout)
    return _respuesta(
        "Ruff",
        "0 hallazgos de código redundante",
        filas,
        cumple=not filas,
    )


def _vulture() -> dict:
    # La configuración (confianza mínima, decoradores de FastAPI y lista
    # blanca de falsos positivos) está en pyproject.toml.
    proceso = _ejecutar("vulture", codigos_validos=(0, 3))
    filas = hallazgos_vulture(proceso.stdout)
    return _respuesta(
        "Vulture",
        "0 elementos sin usar",
        filas,
        cumple=not filas,
    )


def _pylint() -> dict:
    proceso = _ejecutar(
        "pylint",
        *OBJETIVOS,
        "--disable=all",
        "--enable=duplicate-code",
        "--output-format=json2",
        "--score=n",
        codigos_validos=(0, 8),  # 8: avisos de tipo "refactor"
    )
    filas = hallazgos_pylint(proceso.stdout)
    return _respuesta(
        "Pylint",
        "0 bloques repetidos entre archivos",
        filas,
        cumple=not filas,
    )


def _radon() -> dict:
    cc = _ejecutar("radon", "cc", *OBJETIVOS, "-j")
    mi = _ejecutar("radon", "mi", *OBJETIVOS, "-j")
    datos = resumir_radon(cc.stdout, mi.stdout)
    return _respuesta(
        "Radon",
        f"ninguna función peor que el rango {RANGO_MAXIMO_ACEPTADO} "
        "(complejidad 10 o menos)",
        datos["mas_complejas"],
        cumple=datos["excesivas"] == 0,
        total=datos["excesivas"],
        fichas=[
            {"titulo": "complejidad promedio", "valor": datos["promedio"]},
            {"titulo": "funciones analizadas", "valor": datos["funciones"]},
            {
                "titulo": "mantenibilidad mínima "
                f"({datos['mantenibilidad']['archivo']})",
                "valor": datos["mantenibilidad"]["valor"],
            },
        ],
    )


def _cobertura() -> dict:
    # Las pruebas de rendimiento miden tiempos: no deben solaparse con
    # otras mediciones de la aplicación.
    with estado.cerrojo_medicion, tempfile.TemporaryDirectory() as carpeta:
        informe = Path(carpeta) / "cobertura.json"
        proceso = correr_pytest(
            # Scalene real tarda minutos (sobre todo en Windows) y solo
            # aporta las líneas de perfilado_scalene, que otras pruebas ya
            # cubren con simulaciones.
            "--deselect",
            PRUEBA_LENTA,
            "--cov",
            f"--cov-report=json:{informe}",
            entorno=entorno_cobertura(),
        )
        if not informe.exists():
            raise HTTPException(
                500,
                "No se generó el informe (¿está instalado pytest-cov?): "
                + (proceso.stdout + proceso.stderr)[-600:],
            )
        datos = resumir_lineas_sin_ejecutar(
            informe.read_text(encoding="utf-8")
        )
    return _respuesta(
        "coverage",
        "informativo: cada tramo es un candidato a revisar, no un error",
        datos["filas"],
        cumple=None,
        total=datos["total"],
    )


EJECUTORES = {
    "ruff": _ruff,
    "vulture": _vulture,
    "pylint": _pylint,
    "radon": _radon,
    "cobertura": _cobertura,
}


@router.post("/{herramienta}")
def ejecutar_herramienta(
    herramienta: Literal["ruff", "vulture", "pylint", "radon", "cobertura"],
) -> dict:
    """Corre una herramienta de limpieza y devuelve su resumen."""
    return EJECUTORES[herramienta]()
