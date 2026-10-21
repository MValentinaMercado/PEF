# Rutas en grafos: BFS, Dijkstra y A\*

El proyecto consiste en desarrollar un sistema de búsqueda de rutas sobre una red de estaciones conectadas mediante rutas con diferentes pesos o distancias. El objetivo es encontrar caminos entre un origen y un destino utilizando distintos algoritmos y comparar su rendimiento en diferentes condiciones.

Aplicación web desarrollada con **FastAPI** y HTML para construir un grafo ponderado, buscar rutas mediante tres algoritmos (BFS, Dijkstra y A\*) y analizar su eficiencia con mediciones reales.

## Requisitos e instalación

Se requiere Python 3.12 o superior.

```bash
pip install -r requirements.txt
python main.py
```

Una vez iniciada la aplicación, abrir http://127.0.0.1:8000.

## Ventanas

| Ventana          | Dirección        | Contenido                                                                                                                   |
| ---------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 1. Editor        | `/`              | Editor del grafo, búsqueda de rutas y comparación de algoritmos.                                                            |
| 2. Análisis      | `/analisis`      | Benchmark y escalabilidad hasta 100.000 nodos, caché, concurrencia, perfilado (cProfile, line_profiler, Scalene), E/S e IA. |
| 3. Optimización  | `/optimizacion`  | Código redundante, refactorización y herramientas de limpieza.                                                              |
| 4. Pruebas       | `/pruebas`       | Ejecución y visualización de la suite de pruebas.                                                                           |
| 5. Calidad       | `/calidad`       | Herramientas y métricas de calidad del código.                                                                              |
| 6. Documentación | `/documentacion` | Documentación generada con Sphinx.                                                                                          |

La documentación interactiva de la API está disponible en http://127.0.0.1:8000/docs.

## Puertos

- `8000`: aplicación web y API.
- `8081`: servidor de SnakeViz. Se inicia al abrir el perfil de un algoritmo en la ventana Análisis y se cierra junto con la aplicación.

## Estructura del proyecto

```text
main.py             punto de entrada (uvicorn)
api/                capa web: rutas FastAPI, modelos Pydantic y SnakeViz
web/                HTML, CSS y JavaScript de las ventanas
rutas/              lógica del grafo, caché, mediciones, perfilado,
                    concurrencia y E/S
rutas/algoritmos/   BFS, Dijkstra, A* y utilidades comunes
perfiles/           archivos .prof generados por cProfile
tests/              pruebas automatizadas
docs/               fuentes de la documentación (Sphinx)
pyproject.toml      configuración de Ruff, mypy y cobertura
pytest.ini          configuración de pytest
```

## Desarrollo y pruebas

Ejecutar las pruebas:

```bash
pytest
```

Ejecutar las pruebas con cobertura:

```bash
pytest --cov
```

Analizar el código con Ruff:

```bash
ruff check .
ruff format .
```

Comprobar los tipos:

```bash
mypy
```

Como análisis adicional opcional:

```bash
pylint rutas api main.py
```

Para regenerar manualmente la documentación:

```bash
python -m sphinx -b html docs docs/_build/html
```

La aplicación genera la documentación automáticamente al arrancar si todavía no existe.
