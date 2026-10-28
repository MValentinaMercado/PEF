# Optimización y refactorización

La ventana **Optimización** (`/optimizacion`) compara la versión inicial del código con la final. Esta página resume los mismos cambios; las mediciones que los justifican están en la ventana **Análisis**.

## Código redundante eliminado

| Redundancia                                   | Cambio                                                                                                                                                                                                                                      |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Lista de nodos recreada en cada vuelta        | Dijkstra ya no vuelve a listar el grafo; en cada paso solo mira los vecinos del nodo actual.                                                                                                                                                |
| Dos estructuras para lo mismo                 | BFS usa solo el diccionario de predecesores: que un nodo sea clave ya significa que fue descubierto.                                                                                                                                        |
| Comprobación que no cambia el resultado       | Se quitó el filtro `vecino in visitados` de Dijkstra; alcanza con comparar el costo nuevo con el conocido.                                                                                                                                  |
| Inicialización total de las tablas            | Los diccionarios solo contienen los nodos alcanzados; lo que falta se consulta con `costo.get(vecino, math.inf)`.                                                                                                                           |
| Reconstrucción de la ruta duplicada           | Una única función `reconstruir_ruta` en `comunes.py`.                                                                                                                                                                                       |
| Variantes casi idénticas                      | Una implementación por algoritmo: `deque` en BFS y `heapq` en Dijkstra.                                                                                                                                                                     |
| Perfilado copiado y pegado                    | Una función `perfilar_algoritmo` y un bucle sobre `ALGORITMOS`.                                                                                                                                                                             |
| Medición repetida                             | Un solo módulo, `mediciones.py`, para todos los experimentos.                                                                                                                                                                               |
| Bucle principal repetido en Dijkstra y A\*    | Pylint (`duplicate-code`) detectó el mismo bucle en ambos. Ahora existe un único `buscar_con_heap()` en `comunes.py`: A\* le pasa su heurística y Dijkstra no. Se midió que Dijkstra queda dentro del ruido (±3 %) de la versión duplicada. |
| Llamadas a `pytest` repetidas en los routers  | Pylint detectó bloques iguales en `calidad_router` y `pruebas_router`. Ahora `correr_pytest()` y `rutas.procesos.ejecutar_modulo()` concentran la ejecución del proceso, el tiempo máximo y el manejo del error.                            |
| Código muerto                                 | Se eliminó una lectura de memoria cuyo resultado nunca se usaba.                                                                                                                                                                            |
| Entradas de caché que no se pueden reutilizar | La caché se vacía al detectar que el grafo cambió y tiene un tope de 2.048 entradas.                                                                                                                                                        |
| Generación de grafos                          | Cada nodo se conecta con los tres siguientes y el azar sale de un `random.Random(semilla)` propio, en lugar de sortear todos los pares.                                                                                                     |

Dos comprobaciones parecen redundantes y se conservaron: `if actual in cerrados` al sacar un nodo del heap (descarta entradas antiguas del mismo nodo) y la medición de tiempo y memoria en corridas separadas.

## Refactorización

| Aspecto                       | Cambio                                                                                                                         |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| Organización                  | Paquetes con una responsabilidad clara: `rutas`, `rutas/algoritmos`, `api`, `web`, `tests` y `docs`.                           |
| Resultado de los algoritmos   | Todos devuelven `ResultadoBusqueda` (ruta, distancia, nodos explorados).                                                       |
| Elección del algoritmo        | Registro `ALGORITMOS` con firma común.                                                                                         |
| Cálculo, impresión y gráficos | Las funciones devuelven datos; la presentación queda en `api` y `web`.                                                         |
| Grafo                         | `adyacencia`, `nodos()` y `conectar`; se agregaron posiciones, bloqueo de conexiones, renombrar y eliminar.                    |
| Caché                         | El algoritmo se elige al crearla y la clave es solo `(origen, destino)`.                                                       |
| Mediciones                    | Tiempo y pico de memoria por consulta con `tracemalloc`.                                                                       |
| Concurrencia                  | Se compara secuencial, hilos y procesos, con lotes de 10 consultas.                                                            |
| Constantes                    | `TAMANOS_GRAFO`, `CONSULTAS_POR_TAMANO`, `TAMANO_LOTE`, `LADO_MAPA` y `BYTES_POR_KB` reemplazan valores escritos en el código. |
| Documentación y pruebas       | Docstrings con la complejidad de cada algoritmo, ejemplos con `doctest`, referencia con Sphinx, documentación externa con MkDocs y una suite de `pytest`.                       |

## Criterio para optimizar

Una optimización se acepta solo si una medición muestra un problema real: primero una versión clara y correcta, después `cProfile` para ubicar el costo, la mejora y una nueva medición. No se paraleliza la búsqueda de una sola ruta (los hilos no aceleran trabajo de CPU por el GIL) y la caché usa una política simple de descarte de la entrada más antigua.

Para comprobar que quitar código no cambió el comportamiento, las pruebas verifican, entre otras cosas, que A\* y Dijkstra devuelven la misma distancia en cada consulta:

```bash
pytest tests/test_algoritmos.py -q
```

## Herramientas de limpieza

La ventana **Optimización** también ejecuta cinco herramientas que buscan lo que todavía se puede eliminar o simplificar. Cada una responde una pregunta distinta, por eso se usan juntas.

| Herramienta | Qué detecta                                                                                                                         | Criterio                                                      |
|-------------|-------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| Ruff        | Imports y variables sin usar (`F401`, `F841`), redefiniciones, código comentado (`ERA001`) y simplificaciones (`SIM`, `C4`, `PIE`). | 0 hallazgos.                                                  |
| Vulture     | Funciones, clases y variables que nadie usa (código muerto).                                                                        | 0 elementos sin usar.                                         |
| Pylint      | Bloques repetidos entre archivos (`duplicate-code`, R0801).                                                                         | 0 bloques repetidos.                                          |
| Radon       | Complejidad ciclomática por función e índice de mantenibilidad por archivo.                                                         | Ninguna función peor que el rango B (complejidad 10 o menos). |
| coverage    | Líneas que ninguna prueba ejecuta, candidatas a código muerto.                                                                      | Informativo: cada tramo se revisa a mano.                     |

Vulture solo ve nombres escritos en el código, así que genera falsos positivos con FastAPI y con los campos de las `NamedTuple`. Se resolvió en `pyproject.toml` (`ignore_decorators` para rutas y validadores) y en `vulture_lista_blanca.py` (campos de las filas de resultados, cada grupo justificado). Una herramienta con falsos positivos sin resolver se termina ignorando, y por eso se configuró en lugar de bajar la confianza mínima.

Cada herramienta tiene su endpoint `POST /api/optimizacion/{herramienta}` y todas devuelven el mismo formato, que es lo que permite mostrarlas con un único código en la página.
