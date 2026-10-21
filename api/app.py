"""Aplicación FastAPI: API REST + páginas HTML estáticas.

Ejecutar con ``python main.py`` o ``uvicorn api.app:app --reload``. Al
arrancar genera la documentación Sphinx si todavía no existe.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import (
    analisis_router,
    calidad_router,
    documentacion,
    grafo_router,
    optimizacion_router,
    pruebas_router,
    visor_perfiles,
)

WEB = Path(__file__).resolve().parent.parent / "web"
registro = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
    """Prepara lo necesario para ver todo desde el navegador."""
    try:
        await run_in_threadpool(documentacion.construir_si_falta)
    except Exception as error:  # la app debe arrancar igual
        registro.warning("No se pudo generar la documentación: %s", error)
    yield
    visor_perfiles.detener()


app = FastAPI(
    title="Rutas en grafos: BFS, Dijkstra y A*",
    description="Editor de grafos y análisis de rendimiento.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)
app.include_router(grafo_router.router)
app.include_router(analisis_router.router)
app.include_router(pruebas_router.router)
app.include_router(calidad_router.router)
app.include_router(optimizacion_router.router)
app.include_router(documentacion.router)
app.mount("/estatico", StaticFiles(directory=WEB), name="estatico")
app.mount(
    "/sphinx",
    StaticFiles(directory=documentacion.SALIDA, html=True),
    name="sphinx",
)


def _pagina(nombre: str) -> FileResponse:
    return FileResponse(WEB / nombre)


@app.get("/", include_in_schema=False)
def ventana_editor() -> FileResponse:
    """Editor del grafo y búsqueda de rutas."""
    return _pagina("index.html")


@app.get("/analisis", include_in_schema=False)
def ventana_analisis() -> FileResponse:
    """Análisis de rendimiento, caché, concurrencia, perfilado y E/S."""
    return _pagina("analisis.html")


@app.get("/optimizacion", include_in_schema=False)
def ventana_optimizacion() -> FileResponse:
    """Optimización: herramientas de limpieza y refactorización."""
    return _pagina("optimizacion.html")


@app.get("/pruebas", include_in_schema=False)
def ventana_pruebas() -> FileResponse:
    """Resultados de las pruebas."""
    return _pagina("pruebas.html")


@app.get("/calidad", include_in_schema=False)
def ventana_calidad() -> FileResponse:
    """Calidad: Ruff, cobertura y condiciones."""
    return _pagina("calidad.html")


@app.get("/documentacion", include_in_schema=False)
def ventana_documentacion() -> FileResponse:
    """Documentación generada con Sphinx."""
    return _pagina("documentacion.html")
