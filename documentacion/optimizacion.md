# Optimización y refactorización

La ventana **Optimización** (`/optimizacion`) presenta decisiones verificables en el código actual y permite ejecutar bajo demanda cinco controles: Ruff, Vulture, Pylint, Radon y cobertura. No ejecuta herramientas al abrirse. Las mediciones de rendimiento se realizan en la ventana [Análisis](rendimiento.md).

## Decisiones vigentes

| Área | Implementación actual | Motivo |
|---|---|---|
| BFS | `deque` y diccionario de predecesores. | Operaciones eficientes de cola y registro de nodos descubiertos. |
| Dijkstra y A* | `heapq` y bucle común `buscar_con_heap()` en `rutas/algoritmos/comunes.py`. | Cola de prioridad y una única implementación de la relajación. |
| Reconstrucción | `reconstruir_ruta()` compartida. | Unifica el armado del camino. |
| Grafo | Diccionario de listas de adyacencia y versión incremental. | Acceso a vecinos y detección de modificaciones. |
| Caché | `CacheRutas`, con tope de 2.048 entradas e invalidación al cambiar el grafo. | Evita resultados obsoletos y crecimiento ilimitado. |
| Mediciones | `rutas/mediciones.py` separa tiempo y memoria. | `tracemalloc` no contamina la medición temporal. |
| Concurrencia | Comparación secuencial, hilos y procesos sobre lotes. | El costo de procesos no se paga para una única búsqueda. |
| Generación | `random.Random(semilla)` por experimento. | Reproducibilidad sin modificar el generador global. |
| Presentación | `rutas/` calcula, `api/` expone JSON y `web/` presenta. | Mantiene separadas la lógica y la interfaz. |

## Controles de limpieza

Cada herramienta tiene un endpoint `POST /api/optimizacion/{herramienta}`. La interfaz conserva el resultado de la sesión del navegador con su fecha, y solo vuelve a ejecutar una herramienta cuando se solicita un nuevo análisis.

| Herramienta | Qué detecta | Interpretación |
|---|---|---|
| Ruff | Errores, imports y variables sin uso, complejidad y formato. | Los hallazgos requieren revisión y corrección. |
| Vulture | Funciones, clases y variables que parecen no utilizarse. | Revisar falsos positivos por invocación dinámica o decoradores. |
| Pylint | Bloques de código repetidos (`duplicate-code`). | Candidatos a extraer una función común. |
| Radon | Complejidad ciclomática e índice de mantenibilidad. | La configuración del pipeline rechaza rangos C o peores. |
| coverage | Líneas no ejecutadas por la suite. | Es información para orientar pruebas; no demuestra por sí sola que el código sea innecesario. |

Vulture está configurado en `pyproject.toml` para ignorar decoradores de FastAPI y validadores; `vulture_lista_blanca.py` documenta los nombres que no puede resolver estáticamente.

## Criterio de optimización

Una optimización se acepta cuando mantiene la corrección y una medición reproducible muestra una mejora relevante. Para verificar comportamiento se usa `pytest`; para ubicar costos se utilizan `cProfile`, `line_profiler`, `memory_profiler` y Scalene. Los resultados concretos pertenecen a cada ejecución y se consultan en la ventana Análisis, no en cifras fijas de esta guía.
