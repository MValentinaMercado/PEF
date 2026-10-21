Pruebas y perfilado
===================

Ambos se ven directamente en la aplicación web; no hace falta ejecutar
nada aparte.

Pruebas (ventana Pruebas)
-------------------------

La ventana ejecuta ``pytest`` y muestra el resultado de cada prueba,
agrupadas por tipo:

* **unittest**: ``tests/test_algoritmos.py`` y ``tests/test_cache.py``.
* **pytest** con *fixtures* (``tests/conftest.py``): integración de la API
  con ``TestClient``, de los experimentos de análisis y de la ventana de
  calidad.
* **doctest**: los ejemplos ``>>>`` de los docstrings
  (``--doctest-modules``, configurado en ``pytest.ini``).
* **E/S de archivos grandes**: ``tests/test_entrada_salida.py`` comprueba que
  todos los modos de escritura, lectura y procesamiento paralelo producen el
  mismo resultado.
* **timeit**: ``tests/test_rendimiento.py`` comprueba que la caché y BFS
  realmente son más rápidos.

Desde la terminal el comando equivalente es ``pytest -q``; el endpoint es
``POST /api/pruebas/ejecutar``.

Perfilado (ventana Análisis)
----------------------------

* ``cProfile``: llamadas, tiempo propio y acumulado de las funciones más
  costosas de cada algoritmo (:mod:`rutas.perfilado`), con un grafo de
  5.000 nodos y 20 consultas por algoritmo.
* ``SnakeViz``: visualización interactiva de los archivos ``.prof`` que
  deja ``cProfile`` en la carpeta ``perfiles/``. También se puede abrir
  desde la terminal:

  .. code-block:: bash

     snakeviz perfiles/dijkstra.prof

* ``line_profiler``: tiempo de cada línea de BFS, Dijkstra y A*. Agrega un
  costo por línea, así que se compara el porcentaje de cada línea, no el
  tiempo absoluto.
* ``memory_profiler``: memoria total e incremento de cada línea de una
  consulta sobre un grafo de 5.000 nodos.
* ``Scalene``: reparte el tiempo de cada línea entre código Python, código
  nativo y llamadas al sistema, y mide el pico de memoria por línea. Se
  ejecuta como proceso aparte sobre :mod:`rutas.escenario_scalene` y también
  se puede usar desde la terminal:

  .. code-block:: bash

     scalene run rutas/escenario_scalene.py
     scalene view
