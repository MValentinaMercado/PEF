# Descripción funcional

## Problema que resuelve

Elegir un algoritmo de búsqueda de rutas sin medirlo es adivinar. Esta aplicación permite **construir un grafo ponderado, buscar la ruta entre dos nodos con BFS, Dijkstra y A\*** y comparar con datos reales qué cuesta cada uno: tiempo, memoria y nodos explorados. Además muestra cómo escala cada algoritmo hasta 100.000 nodos, dónde gasta el tiempo (perfilado) y si el código cumple los controles de calidad, seguridad y rendimiento del pipeline de integración continua.

Está pensada para el análisis de eficiencia de algoritmos y para practicar un flujo de ingeniería completo (pruebas, calidad, CI y documentación). No es un servicio de navegación.

## Alcance

| Incluido                                                                            | No incluido                                                                                         |
|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| Grafo no dirigido y ponderado, editable desde el navegador.                         | Persistencia: hay un solo grafo en memoria por servidor y se pierde al reiniciarlo.                 |
| BFS, Dijkstra y A\* con resultados comparables.                                     | Pesos negativos (Dijkstra y A\* los suponen no negativos).                                          |
| Benchmark, escalabilidad, caché, concurrencia y entrada/salida de archivos grandes. | Usuarios, autenticación y acceso desde otras computadoras: el servidor escucha solo en `127.0.0.1`. |
| Perfilado de CPU y memoria, y un modelo de IA que predice tiempos.                  | Mapas reales o coordenadas geográficas.                                                             |
| Pruebas, calidad y documentación visibles desde la propia aplicación.               | Despliegue en producción.                                                                           |

## Requisitos funcionales

| Id  | Requisito                                                                                                                     | Dónde se verifica                                     |
|-----|-------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| RF1 | Crear, mover, renombrar y eliminar nodos; crear y eliminar conexiones con peso y bloquearlas sin perder su peso.              | `tests/test_api.py`                                   |
| RF2 | Buscar la ruta con BFS, Dijkstra y A\* y mostrar ruta, distancia, tiempo, memoria y nodos explorados.                         | `tests/test_algoritmos.py`, `tests/test_api.py`       |
| RF3 | Rechazar entradas inválidas (origen igual al destino, algoritmo desconocido, nodo repetido o inexistente) con un error claro. | `tests/test_api.py`                                   |
| RF4 | Ejecutar benchmark y escalabilidad hasta 100.000 nodos y compararlos con la complejidad teórica.                              | `tests/test_analisis.py`                              |
| RF5 | Memorizar rutas en una caché que se invalida sola cuando cambia el grafo.                                                     | `tests/test_cache.py`                                 |
| RF6 | Procesar archivos grandes por lotes, con hilos o procesos, con el mismo resultado en todos los modos.                         | `tests/test_entrada_salida.py`                        |
| RF7 | Perfilar CPU y memoria de cada algoritmo.                                                                                     | `tests/test_perfilado_lineas.py`                      |
| RF8 | Predecir el tiempo de una búsqueda con un modelo de regresión.                                                                | `tests/test_prediccion.py`                            |
| RF9 | Ejecutar las pruebas, mostrar la calidad (SonarQube Cloud) y generar la referencia del código desde la aplicación.                  | `tests/test_optimizacion.py`, `tests/test_calidad.py` |

## Requisitos no funcionales

| Id   | Requisito                                                                                                                                  | Cómo se controla                               |
|------|--------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| RNF1 | Dijkstra resuelve una consulta sobre 100.000 nodos con una mediana menor que 500 ms.                                                       | Performance Gate (`rutas/performance_gate.py`) |
| RNF2 | El pico de memoria de Dijkstra con 100.000 nodos no supera 32 MiB.                                                                         | Memory Gate (`rutas/memory_gate.py`)           |
| RNF3 | Al menos el 80 % del código se ejecuta en las pruebas.                                                                                     | `fail_under` en `pyproject.toml`               |
| RNF4 | Ninguna función con complejidad ciclomática mayor que 10.                                                                                  | Ruff (C90) y Radon                             |
| RNF5 | Sin secretos en el repositorio, sin vulnerabilidades conocidas en las dependencias y sin hallazgos de severidad media o alta en el código. | Gitleaks, pip-audit y Bandit (ver [Seguridad](seguridad.md)) |
| RNF6 | Funciona con Python 3.12 o superior.                                                                                                       | Pipeline de CI (Python 3.12)                   |
| RNF7 | Todo el código tiene tipos y la documentación se construye sin advertencias.                                                               | mypy, `mkdocs build --strict` y `sphinx -W`                             |
