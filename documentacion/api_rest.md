# API REST

Los endpoints se documentan automáticamente en `/docs` (Swagger UI) y `/redoc`. Los ejemplos de consola suponen el servidor en `http://127.0.0.1:8000`.

## Editor

| Método y ruta                 | Descripción                                                |
|-------------------------------|------------------------------------------------------------|
| `GET /api/grafo`              | Estado actual del grafo.                                   |
| `POST /api/grafo/ejemplo`     | Reemplaza el grafo por el ejemplo de 6 nodos.              |
| `DELETE /api/grafo`           | Elimina todos los nodos y conexiones.                      |
| `POST /api/nodos`             | Crea un nodo.                                              |
| `PATCH /api/nodos/{nombre}`   | Mueve o renombra un nodo.                                  |
| `DELETE /api/nodos/{nombre}`  | Elimina un nodo y sus conexiones.                          |
| `PUT /api/aristas`            | Crea o cambia el peso de una conexión.                     |
| `PATCH /api/aristas/bloqueo`  | Bloquea o habilita una conexión.                           |
| `DELETE /api/aristas/{a}/{b}` | Elimina una conexión.                                      |
| `POST /api/rutas`             | Ejecuta y mide BFS, Dijkstra y/o A\*.                      |
| `GET /api/informacion`        | Tabla de funcionamiento y complejidades de cada algoritmo. |

## Análisis

| Método y ruta                             | Descripción                                                                                                        |
|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `POST /api/analisis/benchmark`            | BFS, Dijkstra y A\* con 100, 1.000 y 5.000 nodos.                                                                  |
| `POST /api/analisis/cache`                | Consultas con y sin caché.                                                                                         |
| `POST /api/analisis/escalabilidad`        | Hasta 100.000 nodos: tiempo y memoria frente a la teoría.                                                          |
| `POST /api/analisis/prediccion`           | Mide, entrena y evalúa la regresión que predice tiempos.                                                           |
| `GET /api/analisis/prediccion/recomendar` | Tiempo predicho y algoritmo recomendado (`nodos`, `aristas`, `ponderado`). Requiere entrenar antes.                |
| `POST /api/analisis/concurrencia`         | Secuencial, hilos y procesos.                                                                                      |
| `POST /api/analisis/entrada_salida`       | Buffer, lotes y procesamiento paralelo con un archivo grande.                                                      |
| `POST /api/analisis/perfilado`            | `cProfile` por algoritmo y `memory_profiler` línea por línea; deja un `.prof` por algoritmo en `perfiles/`.        |
| `POST /api/analisis/lineas`               | `line_profiler`: tiempo de cada línea de cada algoritmo.                                                           |
| `POST /api/analisis/scalene`              | `Scalene`: CPU (Python, nativo, sistema) y memoria por línea.                                                      |
| `POST /api/analisis/snakeviz`             | Inicia SnakeViz y devuelve la dirección del perfil de cada algoritmo. Requiere haber ejecutado antes el perfilado. |

## Pruebas, calidad y documentación

| Método y ruta                          | Descripción                                                                              |
|----------------------------------------|------------------------------------------------------------------------------------------|
| `POST /api/pruebas/ejecutar`           | Ejecuta `pytest` y devuelve el resultado de cada prueba.                                 |
| `GET /api/calidad/sonar`               | Quality Gate y métricas del último análisis en SonarQube Cloud.                          |
| `POST /api/optimizacion/{herramienta}` | Ejecuta una herramienta de limpieza: `ruff`, `vulture`, `pylint`, `radon` o `cobertura`. |
| `GET /api/documentacion/estado`        | Indica si la documentación está generada y cuándo.                                       |
| `POST /api/documentacion/generar`      | Regenera la referencia interna del código con Sphinx.                                                    |

## Ejemplos en consola

```bash
# Buscar rutas entre A y F con los tres algoritmos
curl -X POST http://127.0.0.1:8000/api/rutas \
     -H "Content-Type: application/json" \
     -d "{\"origen\":\"A\",\"destino\":\"F\"}"

# Experimentos de la ventana Análisis
curl -X POST http://127.0.0.1:8000/api/analisis/benchmark
curl -X POST http://127.0.0.1:8000/api/analisis/cache

# Pruebas y calidad (también se pueden correr directamente)
curl -X POST http://127.0.0.1:8000/api/pruebas/ejecutar
pytest -q
ruff check .
```

## Referencia de los módulos de la API

El detalle de cada router, esquema y función (parámetros, errores y ejemplos de los *docstrings*) se genera con Sphinx: <a href="../interna/referencia.html#api-modulos-api">Referencia del código, módulos `api`</a>.
