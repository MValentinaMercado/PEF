"""Ventana Calidad: estado del proyecto en SonarQube Cloud.

SonarQube analiza el código en el pipeline de integración continua
(``.github/workflows/ci.yml``). Esta ventana no analiza nada: consulta la API
de SonarQube Cloud y muestra el Quality Gate y las métricas del último
análisis.

El proyecto y la organización salen de ``sonar-project.properties`` (única
fuente de verdad). Con la variable ``SONAR_TOKEN`` se pueden leer proyectos
privados y con ``SONAR_URL`` se cambia el servidor.
"""

import os

import httpx
from fastapi import APIRouter, HTTPException

from rutas.procesos import RAIZ

PROPIEDADES = RAIZ / "sonar-project.properties"
URL_POR_DEFECTO = "https://sonarcloud.io"
TIEMPO_ESPERA_S = 15
METRICAS = {
    "bugs": "Bugs",
    "vulnerabilities": "Vulnerabilidades",
    "security_hotspots": "Puntos críticos de seguridad",
    "code_smells": "Code smells",
    "coverage": "Cobertura (%)",
    "duplicated_lines_density": "Líneas duplicadas (%)",
    "ncloc": "Líneas de código",
    "reliability_rating": "Fiabilidad (calificación)",
    "security_rating": "Seguridad (calificación)",
    "sqale_rating": "Mantenibilidad (calificación)",
}
CALIFICACIONES = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}

router = APIRouter(prefix="/api/calidad")


def parsear_propiedades(texto: str) -> dict[str, str]:
    """Lee un archivo ``.properties`` (``clave=valor``, ``#`` comenta).

    >>> parsear_propiedades("# nota\\nsonar.projectKey=X\\n\\na.b = 1,2\\n")
    {'sonar.projectKey': 'X', 'a.b': '1,2'}
    """
    propiedades = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            propiedades[clave.strip()] = valor.strip()
    return propiedades


def valor_legible(clave: str, valor: str) -> str:
    """Las calificaciones llegan como 1 a 5 y se muestran como A a E.

    >>> valor_legible("security_rating", "1.0")
    'A'
    >>> valor_legible("new_maintainability_rating", "2")
    'B'
    >>> valor_legible("coverage", "93.6")
    '93.6'
    """
    if clave.endswith("_rating"):
        return CALIFICACIONES.get(round(float(valor)), valor)
    return valor


def nombre_metrica(clave: str) -> str:
    """Nombre legible de una métrica (``new_`` es código nuevo).

    >>> nombre_metrica("coverage")
    'Cobertura (%)'
    >>> nombre_metrica("new_coverage")
    'Cobertura (%) en código nuevo'
    """
    base = clave.removeprefix("new_")
    nombre = METRICAS.get(base, base.replace("_", " "))
    return f"{nombre} en código nuevo" if clave.startswith("new_") else nombre


def resumir_sonar(puerta: dict, medidas: dict) -> dict:
    """Une el Quality Gate (``project_status``) con las métricas.

    >>> puerta = {"projectStatus": {"status": "OK", "conditions": [
    ...     {"status": "OK", "metricKey": "new_coverage",
    ...      "comparator": "LT", "errorThreshold": "80",
    ...      "actualValue": "91.2"}]}}
    >>> medidas = {"component": {"measures": [
    ...     {"metric": "sqale_rating", "value": "1.0"},
    ...     {"metric": "bugs", "value": "0"}]}}
    >>> r = resumir_sonar(puerta, medidas)
    >>> r["estado"], r["condiciones"][0]["exigencia"]
    ('OK', '≥ 80')
    >>> [(m["nombre"], m["valor"]) for m in r["medidas"]]
    [('Bugs', '0'), ('Mantenibilidad (calificación)', 'A')]
    """
    estado = puerta["projectStatus"]
    condiciones = [
        {
            "nombre": nombre_metrica(c["metricKey"]),
            "ok": c["status"] == "OK",
            "valor": valor_legible(c["metricKey"], c.get("actualValue", "")),
            "exigencia": (
                f"{'≥' if c['comparator'] == 'LT' else '≤'} "
                f"{valor_legible(c['metricKey'], c['errorThreshold'])}"
            ),
        }
        for c in estado.get("conditions", [])
    ]
    obtenidas = {
        m["metric"]: m.get("value", "")
        for m in medidas["component"]["measures"]
    }
    return {
        "estado": estado["status"],
        "condiciones": condiciones,
        "medidas": [
            {
                "nombre": nombre,
                "valor": valor_legible(clave, obtenidas[clave]),
            }
            for clave, nombre in METRICAS.items()
            if clave in obtenidas
        ],
    }


def _servidor() -> str:
    return os.environ.get("SONAR_URL", URL_POR_DEFECTO).rstrip("/")


def _obtener(ruta: str, parametros: dict[str, str]) -> dict:
    """GET a la API de SonarQube con errores traducidos a mensajes claros."""
    token = os.environ.get("SONAR_TOKEN")
    try:
        respuesta = httpx.get(
            _servidor() + ruta,
            params=parametros,
            auth=(token, "") if token else None,
            timeout=TIEMPO_ESPERA_S,
            follow_redirects=True,
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            502, f"No se pudo conectar con SonarQube Cloud: {error}"
        ) from error
    if respuesta.status_code in (401, 403):
        raise HTTPException(
            502,
            "SonarQube Cloud rechazó la consulta: si el proyecto es privado, "
            "definí la variable de entorno SONAR_TOKEN.",
        )
    if respuesta.status_code == 404:
        raise HTTPException(
            502,
            "SonarQube Cloud no conoce el proyecto: revisá "
            "sonar-project.properties y que el pipeline ya lo haya analizado.",
        )
    if respuesta.status_code >= 400:
        raise HTTPException(
            502, f"SonarQube Cloud respondió {respuesta.status_code}."
        )
    return respuesta.json()


@router.get("/sonar")
def estado_sonar() -> dict:
    """Quality Gate y métricas del último análisis en SonarQube Cloud."""
    propiedades = parsear_propiedades(PROPIEDADES.read_text(encoding="utf-8"))
    proyecto = propiedades["sonar.projectKey"]
    puerta = _obtener(
        "/api/qualitygates/project_status", {"projectKey": proyecto}
    )
    medidas = _obtener(
        "/api/measures/component",
        {"component": proyecto, "metricKeys": ",".join(METRICAS)},
    )
    return resumir_sonar(puerta, medidas) | {
        "proyecto": proyecto,
        "organizacion": propiedades["sonar.organization"],
        "panel": f"{_servidor()}/summary/overall?id={proyecto}",
    }
