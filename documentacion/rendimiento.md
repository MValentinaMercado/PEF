# Rendimiento

## Qué se mide

| Aspecto            | Herramienta                                    | Dónde ver el resultado                           |
|--------------------|------------------------------------------------|--------------------------------------------------|
| Benchmark          | `rutas/benchmark.py` y `rutas/mediciones.py` (`perf_counter`)                | Ventana Análisis; `POST /api/analisis/benchmark` |
| Escalabilidad      | `rutas/escalabilidad.py` (hasta 100.000 nodos) | Ventana Análisis, contra la complejidad teórica  |
| Profiling de CPU   | `cProfile` (+ SnakeViz) y `line_profiler`      | Ventana Análisis; `perfiles/*.prof`              |
| Consumo de memoria | `tracemalloc`, `memory_profiler` y Scalene     | Ventana Análisis                                 |
| Regresiones        | Performance Gate y Memory Gate                 | Pipeline de CI ([Mantenimiento](mantenimiento.md))                 |

## Complejidad

La complejidad temporal y espacial de BFS, Dijkstra y A\* está en la tabla de [Algoritmos y estructuras de datos](algoritmos.md). La ventana Análisis compara la curva medida con la teórica para confirmar que el crecimiento es el esperado.

## Interpretación de resultados

Los tiempos, el consumo de memoria y las funciones más costosas dependen del equipo, de la carga y de la versión de Python. Por eso esta documentación no fija cifras de una corrida anterior como si fueran actuales. Para consultar resultados vigentes, ejecutar el experimento correspondiente desde la ventana Análisis y leer la fecha y los datos de esa ejecución. Los gates de CI publican sus valores en el registro de GitHub Actions.

El Performance Gate utiliza el umbral definido en `rutas/performance_gate.py`; el Memory Gate utiliza el límite definido en `rutas/memory_gate.py`. Los umbrales son configuración del proyecto, no resultados medidos.

Las conclusiones de las tablas de Análisis se redactan a partir de los números de cada ejecución, sin suponer un ganador: si dos algoritmos difieren menos del 5 %, el texto los presenta como prácticamente iguales.

## Cómo reproducirlo

```bash
python -m rutas.performance_gate        # tiempo según el umbral configurado
python -m rutas.memory_gate             # memoria según el límite configurado
python -c "from pathlib import Path; from rutas.perfilado import ejecutar_perfilado; ejecutar_perfilado(carpeta_prof=Path('perfiles'))"
snakeviz perfiles/dijkstra.prof         # visualización del perfil
```

Ambos gates aceptan `--nodos` y un límite (`--umbral-ms` o `--limite-mib`) para probarlos con otros valores; consultar `--help` para los valores admitidos. En el pipeline se ejecutan en la etapa `rendimiento`, que solo corre si las demás aprobaron.
