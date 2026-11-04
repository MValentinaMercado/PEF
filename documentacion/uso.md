# Instalación y uso

Requiere Python 3.12 o superior.

```bash
pip install -r requirements.txt
python main.py
```

Con ese único comando se levanta todo. Abrir <http://127.0.0.1:8000>:

| Ventana | Dirección | Contenido |
|---|---|---|
| Editor | `/` | Edición del grafo, búsqueda de rutas y comparación de algoritmos. |
| Análisis | `/analisis` | Experimentos de rendimiento, concurrencia, perfilado, E/S y predicción. |
| Optimización | `/optimizacion` | Decisiones de diseño y controles de limpieza ejecutados bajo demanda. |
| Pruebas | `/pruebas` | Suite de pytest ejecutada bajo demanda y detalle de casos. |
| Calidad | `/calidad` | Quality Gate de SonarQube y última corrida real de GitHub Actions. |
| Documentación | `/documentacion` | Guías externas con MkDocs y referencia de código con Sphinx. |

La documentación interactiva de la API que genera FastAPI está en <http://127.0.0.1:8000/docs>.

## Resultados guardados en la pestaña

Abrir una ventana no ejecuta experimentos. Los resultados de Análisis, Optimización, Pruebas y Calidad, la consulta del modelo de predicción y la última comparación del Editor se guardan en el `sessionStorage` de la pestaña y se muestran al volver, con la fecha de la ejecución y sin presentarlos como nuevos. Al cerrar la pestaña se pierden.

- El Editor restaura su última comparación solo si el grafo y los nodos de origen y destino siguen siendo los mismos; si no, la descarta.
- Restaurar el perfilado en Análisis no vuelve a iniciar SnakeViz: el servidor se inicia únicamente al pedir un perfil.
- Los textos de conclusión de las tablas de Análisis se generan en el navegador a partir de los resultados mostrados, también al restaurarlos. Dos valores que difieren menos del 5 % se describen como prácticamente iguales (`TOLERANCIA_IGUALES` en `web/js/comun.js`).

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
mkdocs serve -a 127.0.0.1:8001                # este sitio en http://127.0.0.1:8001
python -m sphinx -b html docs docs/_build/html # referencia interna
```

Al arrancar, la aplicación genera ambas documentaciones solo si todavía no existen. Los botones de la ventana Documentación permiten regenerarlas manualmente.

## Estructura del proyecto

```text
main.py            punto de entrada (uvicorn)
api/               capa web: rutas FastAPI, modelos pydantic, SnakeViz
web/               HTML, CSS y JavaScript de las ventanas
rutas/             lógica pura (sin web): grafo, algoritmos, caché,
                   mediciones, perfilado, concurrencia y E/S
rutas/algoritmos/  BFS, Dijkstra, A* y utilidades comunes
perfiles/          archivos .prof generados por cProfile (SnakeViz)
tests/             suite pytest (incluye unittest, doctest y mediciones con timeit)
documentacion/     documentación externa (MkDocs)
docs/              referencia interna del código (Sphinx)
mkdocs.yml         configuración de MkDocs
pyproject.toml     configuración de Ruff y cobertura
pytest.ini         configuración de pytest (incluye doctest)
```
