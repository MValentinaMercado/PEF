"""Generación de las dos documentaciones (Sphinx y MkDocs) y su estado."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "docs"
SALIDA = FUENTE / "_build" / "html"
SALIDA.mkdir(parents=True, exist_ok=True)  # para poder montarla siempre

# Documentación externa (MkDocs): se genera fuera de ``site/`` para no pisar
# lo que publica el CI.
SALIDA_EXTERNA = FUENTE / "_build" / "mkdocs"
SALIDA_EXTERNA.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/documentacion")


def disponible() -> bool:
    """Indica si ya existe el HTML generado."""
    return (SALIDA / "index.html").exists()


def disponible_externa() -> bool:
    """Indica si ya existe el sitio MkDocs generado."""
    return (SALIDA_EXTERNA / "index.html").exists()


def _ejecutar(orden: list[str]) -> None:
    """Corre una herramienta de documentación; ``RuntimeError`` si falla."""
    proceso = subprocess.run(
        orden,
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,  # el código de salida se revisa a mano
    )
    if proceso.returncode != 0:
        raise RuntimeError((proceso.stdout + proceso.stderr)[-800:])


def construir() -> None:
    """Ejecuta Sphinx; lanza ``RuntimeError`` si falla."""
    _ejecutar(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-q",
            str(FUENTE),
            str(SALIDA),
        ]
    )


def construir_externa() -> None:
    """Ejecuta MkDocs; lanza ``RuntimeError`` si falla."""
    _ejecutar(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "-q",
            "-f",
            str(RAIZ / "mkdocs.yml"),
            "-d",
            str(SALIDA_EXTERNA),
        ]
    )


def construir_si_falta() -> None:
    """Genera cada documentación solo si todavía no existe."""
    if not disponible():
        construir()
    if not disponible_externa():
        construir_externa()


def _estado(carpeta: Path) -> dict:
    """Estado de una carpeta de salida para la interfaz."""
    indice = carpeta / "index.html"
    if not indice.exists():
        return {"disponible": False, "generada": None}
    momento = datetime.fromtimestamp(indice.stat().st_mtime)
    return {
        "disponible": True,
        "generada": momento.strftime("%d/%m/%Y %H:%M:%S"),
    }


def estado_documentacion() -> dict:
    """Estado de la referencia interna (Sphinx)."""
    return _estado(SALIDA)


def estado_externa() -> dict:
    """Estado de la documentación externa (MkDocs)."""
    return _estado(SALIDA_EXTERNA)


@router.get("/estado")
def obtener_estado() -> dict:
    """Dice si la documentación está generada y cuándo."""
    return estado_documentacion()


@router.post("/generar")
def regenerar() -> dict:
    """Vuelve a generar la documentación con Sphinx."""
    try:
        construir()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise HTTPException(500, f"Sphinx falló: {error}") from error
    return estado_documentacion()


@router.get("/externa/estado")
def obtener_estado_externa() -> dict:
    """Dice si la documentación MkDocs está generada y cuándo."""
    return estado_externa()


@router.post("/externa/generar")
def regenerar_externa() -> dict:
    """Vuelve a generar la documentación externa con MkDocs."""
    try:
        construir_externa()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise HTTPException(500, f"MkDocs falló: {error}") from error
    return estado_externa()
