"""Ventana Calidad: estado del pipeline de CI en GitHub Actions.

El pipeline (``.github/workflows/ci.yml``) es quien ejecuta los controles y
decide si el código se aprueba. Esta ventana **no vuelve a ejecutarlos ni los
simula**: consulta la API de GitHub y muestra el resultado real de la última
corrida de la rama principal, sus etapas, qué paso falló y el historial.

El repositorio sale de la variable ``GITHUB_REPOSITORY`` (``usuario/repo``) o,
si no existe, del remoto ``origin`` de ``.git/config``. Para repositorios
privados (o para no agotar el límite de consultas anónimas) se usa la variable
``GITHUB_TOKEN``, con permiso de solo lectura de Actions. El token se lee en
el servidor y nunca se envía al navegador.
"""

import os
import re
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException

from rutas.procesos import RAIZ

URL_API = "https://api.github.com"
FLUJO = "ci.yml"
RAMA = "main"
HISTORIAL = 5
TIEMPO_ESPERA_S = 15
PATRON_REPOSITORIO = re.compile(
    r"github\.com[:/]+(?P<repo>[\w.-]+/[\w.-]+?)(?:\.git)?/?$"
)
PATRON_ORIGEN = re.compile(
    r'\[remote "origin"\][^\[]*?\burl\s*=\s*(?P<url>\S+)'
)
ESTADOS = {
    "success": "aprobado",
    "failure": "rechazado",
    "timed_out": "rechazado",
    "cancelled": "cancelado",
    "skipped": "omitido",
}
ERRORES_HTTP = {
    401: "GitHub rechazó el token: revisá la variable GITHUB_TOKEN.",
    403: (
        "GitHub rechazó la consulta (límite de consultas o falta de "
        "permisos): definí la variable GITHUB_TOKEN."
    ),
    404: (
        "GitHub no encontró el repositorio o el flujo ci.yml: si el "
        "repositorio es privado, definí la variable GITHUB_TOKEN."
    ),
}

router = APIRouter(prefix="/api/calidad")


def repositorio_desde_url(url: str) -> str | None:
    """``usuario/repo`` a partir de la dirección de un remoto de Git.

    >>> repositorio_desde_url("https://github.com/ana/rutas.git")
    'ana/rutas'
    >>> repositorio_desde_url("git@github.com:ana/rutas")
    'ana/rutas'
    >>> repositorio_desde_url("https://gitlab.com/ana/rutas.git") is None
    True
    """
    coincidencia = PATRON_REPOSITORIO.search(url)
    return coincidencia["repo"] if coincidencia else None


def repositorio() -> str:
    """Repositorio a consultar: variable de entorno o remoto ``origin``."""
    definido = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if definido:
        return definido
    try:
        texto = (RAIZ / ".git" / "config").read_text(encoding="utf-8")
    except OSError:
        texto = ""
    origen = PATRON_ORIGEN.search(texto)
    encontrado = origen and repositorio_desde_url(origen["url"])
    if not encontrado:
        raise HTTPException(
            409,
            "No se sabe qué repositorio consultar: definí la variable "
            "GITHUB_REPOSITORY (usuario/repo) o agregá el remoto origin.",
        )
    return encontrado


def _obtener(ruta: str, parametros: dict[str, str | int]) -> dict:
    """GET a la API de GitHub con los errores traducidos a mensajes claros."""
    cabeceras = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    try:
        respuesta = httpx.get(
            URL_API + ruta,
            params=parametros,
            headers=cabeceras,
            timeout=TIEMPO_ESPERA_S,
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            502, f"No se pudo conectar con GitHub: {error}"
        ) from error
    if respuesta.status_code >= 400:
        raise HTTPException(
            502,
            ERRORES_HTTP.get(
                respuesta.status_code,
                f"GitHub respondió {respuesta.status_code}.",
            ),
        )
    return respuesta.json()


def estado_legible(estado: str | None, resultado: str | None) -> str:
    """Estado de una corrida o etapa en una palabra.

    >>> estado_legible("completed", "success")
    'aprobado'
    >>> estado_legible("completed", "failure")
    'rechazado'
    >>> estado_legible("in_progress", None)
    'en curso'
    """
    if estado != "completed":
        return "en curso"
    return ESTADOS.get(resultado or "", "sin resultado")


def segundos_entre(inicio: str | None, fin: str | None) -> float | None:
    """Segundos entre dos fechas ISO 8601 de GitHub.

    >>> segundos_entre("2026-10-01T10:00:00Z", "2026-10-01T10:02:30Z")
    150.0
    >>> segundos_entre(None, "2026-10-01T10:02:30Z") is None
    True
    """
    if not inicio or not fin:
        return None
    formato = datetime.fromisoformat
    return (
        formato(fin.replace("Z", "+00:00"))
        - formato(inicio.replace("Z", "+00:00"))
    ).total_seconds()


def _enlace(url: str | None) -> str | None:
    """Solo se entregan al navegador direcciones https."""
    return url if url and url.startswith("https://") else None


def resumir_corrida(corrida: dict) -> dict:
    """Datos de una corrida del pipeline para mostrar.

    >>> r = resumir_corrida({"run_number": 7, "status": "completed",
    ...     "conclusion": "success", "head_sha": "abcdef1234",
    ...     "event": "push", "display_title": "Mejora",
    ...     "run_started_at": "2026-10-01T10:00:00Z",
    ...     "updated_at": "2026-10-01T10:01:00Z",
    ...     "html_url": "https://github.com/a/b/actions/runs/1"})
    >>> r["numero"], r["estado"], r["commit"], r["segundos"]
    (7, 'aprobado', 'abcdef1', 60.0)
    """
    return {
        "numero": corrida["run_number"],
        "estado": estado_legible(corrida["status"], corrida.get("conclusion")),
        "commit": corrida["head_sha"][:7],
        "evento": corrida.get("event", ""),
        "titulo": corrida.get("display_title", ""),
        "inicio": corrida.get("run_started_at"),
        "actualizada": corrida.get("updated_at"),
        "segundos": segundos_entre(
            corrida.get("run_started_at"), corrida.get("updated_at")
        ),
        "url": _enlace(corrida.get("html_url")),
    }


def resumir_etapas(trabajos: list[dict]) -> list[dict]:
    """Resume cada job real, sus pasos y el primer paso que falló.

    >>> filas = resumir_etapas([{"name": "Pruebas", "status": "completed",
    ...     "conclusion": "failure", "html_url": "https://x",
    ...     "steps": [{"name": "Instalar", "conclusion": "success"},
    ...               {"name": "pytest", "conclusion": "failure"}]}])
    >>> filas[0]["estado"], filas[0]["paso_fallido"]
    ('rechazado', 'pytest')
    """
    return [
        {
            "nombre": trabajo["name"],
            "estado": estado_legible(
                trabajo["status"], trabajo.get("conclusion")
            ),
            "segundos": segundos_entre(
                trabajo.get("started_at"), trabajo.get("completed_at")
            ),
            "controles": [
                {
                    "nombre": paso.get("name", "Paso sin nombre"),
                    "estado": estado_legible(
                        paso.get("status", "completed"), paso.get("conclusion")
                    ),
                }
                for paso in trabajo.get("steps", [])
            ],
            "paso_fallido": next(
                (
                    paso["name"]
                    for paso in trabajo.get("steps", [])
                    if paso.get("conclusion") == "failure"
                ),
                None,
            ),
            "url": _enlace(trabajo.get("html_url")),
        }
        for trabajo in trabajos
    ]


def _resumen_historial(historial: list[dict]) -> str:
    """Cuenta las corridas del historial por estado."""
    cuenta = {
        estado: sum(c["estado"] == estado for c in historial)
        for estado in ("aprobado", "rechazado", "cancelado", "omitido")
    }
    en_curso = sum(c["estado"] == "en curso" for c in historial)
    sin_resultado = len(historial) - sum(cuenta.values()) - en_curso
    return (
        f" En las últimas {len(historial)} corridas: "
        f"{cuenta['aprobado']} aprobadas, {cuenta['rechazado']} rechazadas, "
        f"{cuenta['cancelado']} canceladas, {cuenta['omitido']} omitidas, "
        f"{en_curso} en curso y {sin_resultado} sin resultado."
    )


def _detalle_no_aprobadas(etapas: list[dict]) -> str:
    """Lista las etapas no aprobadas, con el paso que falló si se conoce."""
    no_aprobadas = [
        f"{e['nombre']} ({e['estado']}"
        + (f", paso «{e['paso_fallido']}»" if e["paso_fallido"] else "")
        + ")"
        for e in etapas
        if e["estado"] != "aprobado"
    ]
    return "; ".join(no_aprobadas) if no_aprobadas else "sin detalle de etapas"


def concluir_ci(
    ultima: dict, etapas: list[dict], historial: list[dict]
) -> str:
    """Redacta un resumen del resultado y de las cinco corridas más recientes.

    >>> ult = {"numero": 12, "estado": "aprobado"}
    >>> et = [{"nombre": "Pruebas", "estado": "aprobado",
    ...        "paso_fallido": None}]
    >>> "aprobada" in concluir_ci(ult, et, [ult])
    True
    >>> ult = {"numero": 13, "estado": "rechazado"}
    >>> et = [{"nombre": "Pruebas", "estado": "rechazado",
    ...        "paso_fallido": "pytest"}]
    >>> "pytest" in concluir_ci(ult, et, [ult])
    True
    """
    numero = ultima["numero"]
    resumen = _resumen_historial(historial)
    if ultima["estado"] == "en curso":
        return f"La corrida #{numero} todavía se está ejecutando." + resumen
    if ultima["estado"] == "aprobado":
        return (
            f"La última corrida en {RAMA} (#{numero}) fue aprobada: "
            f"{len(etapas)} etapas terminaron bien." + resumen
        )
    return (
        f"La última corrida en {RAMA} (#{numero}) terminó "
        f"{ultima['estado']}. Etapas no aprobadas: "
        f"{_detalle_no_aprobadas(etapas)}." + resumen
    )


@router.get("/ci")
def estado_ci() -> dict:
    """Última corrida del pipeline en GitHub Actions, etapas e historial."""
    repo = repositorio()
    corridas = _obtener(
        f"/repos/{repo}/actions/workflows/{FLUJO}/runs",
        {"branch": RAMA, "per_page": HISTORIAL},
    )["workflow_runs"]
    if not corridas:
        raise HTTPException(
            404, f"El flujo {FLUJO} todavía no se ejecutó en {RAMA}."
        )
    historial = [resumir_corrida(c) for c in corridas]
    trabajos = _obtener(
        f"/repos/{repo}/actions/runs/{corridas[0]['id']}/jobs",
        {"per_page": 50},
    )["jobs"]
    etapas = resumir_etapas(trabajos)
    return {
        "repositorio": repo,
        "rama": RAMA,
        "ultima": historial[0],
        "etapas": etapas,
        "historial": historial,
        "conclusion": concluir_ci(historial[0], etapas, historial),
        "panel": f"https://github.com/{repo}/actions/workflows/{FLUJO}",
    }
