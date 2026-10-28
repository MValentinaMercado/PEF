# Instalación y uso

Requiere Python 3.12 o superior.

```bash
pip install -r requirements.txt
python main.py
```

Con ese único comando se levanta todo. Abrir <http://127.0.0.1:8000>:

| Ventana           | Dirección        | Contenido                                                                                                                                                                   |
|-------------------|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 · Editor        | `/`              | Editor del grafo, búsqueda de rutas, tabla de resultados y tabla de referencia de los algoritmos.                                                                           |
| 2 · Análisis      | `/analisis`      | Benchmark, caché, concurrencia, perfilado (`cProfile`, `SnakeViz`, `line_profiler`, `memory_profiler` y `Scalene`), E/S de archivos grandes y predicción de tiempos con IA. |
| 3 · Optimización  | `/optimizacion`  | Código redundante eliminado y refactorización, comparando la versión inicial con la final.                                                                                  |
| 4 · Pruebas       | `/pruebas`       | Ejecuta y muestra la suite de pruebas.                                                                                                                                      |
| 5 · Calidad       | `/calidad`       | Quality Gate y métricas de SonarQube Cloud.                                                                                                                                 |
| 6 · Documentación | `/documentacion` | Referencia interna del código, generada con Sphinx (ver [Mantenimiento](mantenimiento.md)).                                                                                                                                    |

La documentación interactiva de la API que genera FastAPI está en <http://127.0.0.1:8000/docs>.

## Puertos utilizados

- `8000`: aplicación web y API.
- `8081`: servidor de SnakeViz, que se inicia solo la primera vez que se abre el perfil de un algoritmo en la ventana Análisis y se cierra junto con la aplicación.

## Documentación

Hay dos documentaciones, cada una con su herramienta:

| Documentación                | Herramienta     | Carpeta          | Contenido                                                       |
|------------------------------|-----------------|------------------|-----------------------------------------------------------------|
| Externa (este sitio)         | MkDocs Material | `documentacion/` | Funcional, arquitectura, uso, diseño, API, pruebas, seguridad.  |
| Interna (referencia del código) | Sphinx       | `docs/`          | Módulos, clases y funciones, generados de los *docstrings*.     |

```bash
mkdocs serve                                   # este sitio en http://127.0.0.1:8001
python -m sphinx -b html docs docs/_build/html # referencia interna
```

Al arrancar, la aplicación genera la referencia interna si todavía no existe (ventana 6). El botón de esa ventana la regenera.

## Estructura del proyecto

```text
main.py            punto de entrada (uvicorn)
api/               capa web: rutas FastAPI, modelos pydantic, SnakeViz
web/               HTML, CSS y JavaScript de las ventanas
rutas/             lógica pura (sin web): grafo, algoritmos, caché,
                   mediciones, perfilado, concurrencia y E/S
rutas/algoritmos/  BFS, Dijkstra, A* y utilidades comunes
perfiles/          archivos .prof generados por cProfile (SnakeViz)
tests/             pruebas unittest / pytest / timeit
documentacion/     documentación externa (MkDocs)
docs/              referencia interna del código (Sphinx)
mkdocs.yml         configuración de MkDocs
pyproject.toml     configuración de Ruff y cobertura
pytest.ini         configuración de pytest (incluye doctest)
```
