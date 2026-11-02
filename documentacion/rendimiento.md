# Rendimiento

## Qué se mide

| Aspecto            | Herramienta                                    | Dónde ver el resultado                           |
|--------------------|------------------------------------------------|--------------------------------------------------|
| Benchmark          | `timeit` y `rutas/benchmark.py`                | Ventana Análisis; `POST /api/analisis/benchmark` |
| Escalabilidad      | `rutas/escalabilidad.py` (hasta 100.000 nodos) | Ventana Análisis, contra la complejidad teórica  |
| Profiling de CPU   | `cProfile` (+ SnakeViz) y `line_profiler`      | Ventana Análisis; `perfiles/*.prof`              |
| Consumo de memoria | `tracemalloc`, `memory_profiler` y Scalene     | Ventana Análisis                                 |
| Regresiones        | Performance Gate y Memory Gate                 | Pipeline de CI ([Mantenimiento](mantenimiento.md))                 |

## Complejidad

La complejidad temporal y espacial de BFS, Dijkstra y A\* está en la tabla de [Algoritmos y estructuras de datos](algoritmos.md). La ventana Análisis compara la curva medida con la teórica para confirmar que el crecimiento es el esperado.

## Resultados de referencia

Medidos con Python 3.12.3 en una sola máquina Linux. Sirven como referencia, no como garantía: el tiempo cambia con la computadora (por eso el pipeline usa la mediana de varias corridas y un umbral con margen), mientras que la memoria medida con `tracemalloc` no cambia entre corridas.

| Medición (Dijkstra, 100.000 nodos) | Resultado | Límite | Estado   |
|------------------------------------|-----------|--------|----------|
| Mediana por consulta               | 179 ms    | 500 ms | Aprobado |
| Pico de memoria                    | 15,2 MiB  | 32 MiB | Aprobado |

Detección de una regresión: con el cambio de `regresion_rendimiento.patch` (lista en lugar de conjunto), Dijkstra con 20.000 nodos pasa de una mediana de 12,6 ms a 306 ms y el Performance Gate falla.

## Profiling de CPU

Funciones con más tiempo propio, con un grafo de 5.000 nodos y 20 consultas por algoritmo (`rutas.perfilado.ejecutar_perfilado`):

| Algoritmo | Función               | Llamadas | Tiempo propio (s) |
|-----------|-----------------------|----------|-------------------|
| BFS       | `bfs`                 | 20       | 0,035             |
| BFS       | `vecinos_habilitados` | 39.442   | 0,010             |
| Dijkstra  | `buscar_con_heap`     | 20       | 0,094             |
| Dijkstra  | `dict.get`            | 237.156  | 0,032             |
| A\*       | `buscar_con_heap`     | 20       | 0,123             |
| A\*       | `heuristica`          | 64.039   | 0,020             |

El tiempo se concentra en el bucle principal y en las consultas al diccionario de costos, que es lo esperado para estos algoritmos. En A\* la heurística se calcula decenas de miles de veces, pero sigue costando menos que el bucle. Sin `carpeta_prof` la función solo devuelve las tablas; con ella además deja un `.prof` por algoritmo.

## Cómo reproducirlo

```bash
python -m rutas.performance_gate        # tiempo (falla si mediana >= 500 ms)
python -m rutas.memory_gate             # memoria (falla si pico > 32 MiB)
python -c "from pathlib import Path; from rutas.perfilado import ejecutar_perfilado; ejecutar_perfilado(carpeta_prof=Path('perfiles'))"
snakeviz perfiles/dijkstra.prof         # visualización del perfil
```

Ambos gates aceptan `--nodos` y un límite (`--umbral-ms` o `--limite-mib`) para probarlos con otros valores. En el pipeline se ejecutan en la etapa `rendimiento`, que solo corre si las demás aprobaron.
