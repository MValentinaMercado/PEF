"""Generación de la documentación Sphinx y su estado."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "docs"
SALIDA = FUENTE / "_build" / "html"
SALIDA.mkdir(parents=True, exist_ok=True)  # para poder montarla siempre

router = APIRouter(prefix="/api/documentacion")


def disponible() -> bool:
    """Indica si ya existe el HTML generado."""
    return (SALIDA / "index.html").exists()


def construir() -> None:
    """Ejecuta Sphinx; lanza ``RuntimeError`` si falla."""
    proceso = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-q",
            str(FUENTE),
            str(SALIDA),
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,  # el código de salida se revisa a mano
    )
    if proceso.returncode != 0:
        raise RuntimeError((proceso.stdout + proceso.stderr)[-800:])


def construir_si_falta() -> None:
    """Genera la documentación solo si todavía no existe."""
    if not disponible():
        construir()


def estado_documentacion() -> dict:
    """Estado para la interfaz."""
    if not disponible():
        return {"disponible": False, "generada": None}
    momento = datetime.fromtimestamp((SALIDA / "index.html").stat().st_mtime)
    return {
        "disponible": True,
        "generada": momento.strftime("%d/%m/%Y %H:%M:%S"),
    }


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
