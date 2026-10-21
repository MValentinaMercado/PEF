Rutas en grafos: BFS, Dijkstra y A*
===================================

Aplicación web mediante **FastAPI**  y **HTML** para construir un grafo ponderado,
buscar rutas con tres algoritmos y analizar su eficiencia. Se organiza en
seis ventanas:

1. **Editor**: crear, mover, renombrar y eliminar nodos; conectar con pesos;
   bloquear conexiones; ejecutar BFS, Dijkstra y A* y comparar sus
   resultados reales (ruta, distancia, tiempo, memoria y nodos explorados).
2. **Análisis**: benchmark y escalabilidad hasta 100.000 nodos contra la
   teoría, caché, concurrencia, perfilado (``cProfile``, ``SnakeViz``,
   ``line_profiler``, ``memory_profiler`` y ``Scalene``), entrada/salida con
   archivos grandes y un componente de IA (:doc:`ia`).
3. **Optimización**: qué código redundante se eliminó y cómo se reorganizó
   el proyecto.
4. **Pruebas**: ejecución de la suite (``unittest``, ``pytest``,
   ``doctest`` y ``timeit``).
5. **Calidad**: estado del proyecto en SonarQube Cloud (Quality Gate y
   métricas); el pipeline de CI aplica además Ruff, mypy, Vulture, Pylint,
   Bandit, pip-audit y la cobertura mínima.
6. **Documentación**: esta documentación, generada con Sphinx.

Cada tabla o resultado de la aplicación muestra, en un recuadro que aparece
al pasar el cursor sobre el signo ``</>``, el endpoint y el comando de consola
que producen esos mismos datos (ver :doc:`api_rest`).

.. toctree::
   :maxdepth: 2
   :caption: Contenido

   uso
   algoritmos
   optimizacion
   ia
   api_rest
   pruebas
   calidad
   referencia
