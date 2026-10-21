# Rutas en grafos: BFS, Dijkstra y A\*

Aplicación web hecha con **FastAPI** y HTML para construir un grafo
ponderado, buscar rutas con tres algoritmos (BFS, Dijkstra y A\*) y analizar
su eficiencia con mediciones reales.

## Requisitos e instalación

Python 3.12 o superior.

```bash
pip install -r requirements.txt
python main.py
```

Con eso se levanta todo. Abrir <http://127.0.0.1:8000>.

## Ventanas

| Ventana           | Dirección        | Contenido                                                        |
| ----------------- | ---------------- | ---------------------------------------------------------------- |
| 1 · Editor        | `/`              | Editor del grafo, búsqueda de rutas y comparación de algoritmos. |
| 2 · Análisis      | `/analisis`      | Benchmark y escalabilidad hasta 100.000 nodos, caché, concurrencia, perfilado (cProfile, line_profiler, Scalene), E/S e IA. |
| 3 · Optimización  | `/optimizacion`  | Código redundante, refactorización y herramientas de limpieza.   |
| 4 · Pruebas       | `/pruebas`       | Ejecuta y muestra la suite de pruebas.                           |
| 5 · Calidad       | `/calidad`       | Ruff, cobertura y condiciones de calidad.                        |
| 6 · Documentación | `/documentacion` | Documentación generada con Sphinx.                               |

La documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>.

### Puertos

- `8000`: aplicación web y API.
- `8081`: servidor de SnakeViz. Se inicia solo al abrir el perfil de un
  algoritmo en la ventana Análisis y se cierra junto con la aplicación.

## Estructura

```text
main.py            punto de entrada (uvicorn)
api/               capa web: rutas FastAPI, modelos pydantic, SnakeViz
web/               HTML, CSS y JavaScript de las ventanas
rutas/             lógica pura (sin web): grafo, caché, mediciones,
                   perfilado, concurrencia y E/S
rutas/algoritmos/  BFS, Dijkstra, A* y utilidades comunes
perfiles/          archivos .prof generados por cProfile (SnakeViz)
tests/             pruebas unittest / pytest / timeit
docs/              fuentes de la documentación (Sphinx)
pyproject.toml     configuración de Ruff, mypy y cobertura
pytest.ini         configuración de pytest (incluye doctest)
```

## Desarrollo

```bash
pytest                       # pruebas (incluye doctests)
pytest --cov                 # pruebas + cobertura (mínimo 80 %)
ruff check .                 # análisis estático
ruff format .                # formato (líneas de hasta 79 caracteres)
mypy                         # tipado (configurado en pyproject.toml)
pylint rutas api main.py     # análisis adicional (opcional)
```

Para regenerar la documentación a mano:

```bash
python -m sphinx -b html docs docs/_build/html
```

La app la genera sola al arrancar si todavía no existe.
