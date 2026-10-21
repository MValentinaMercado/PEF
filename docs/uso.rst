Instalación y uso
=================

Requiere Python 3.12 o superior.

.. code-block:: bash

   pip install -r requirements.txt
   python main.py

Con ese único comando se levanta todo. Abrir http://127.0.0.1:8000:

.. list-table::
   :header-rows: 1
   :widths: 18 16 66

   * - Ventana
     - Dirección
     - Contenido
   * - 1 · Editor
     - ``/``
     - Editor del grafo, búsqueda de rutas, tabla de resultados y tabla de
       referencia de los algoritmos.
   * - 2 · Análisis
     - ``/analisis``
     - Benchmark, caché, concurrencia, perfilado (``cProfile``,
       ``SnakeViz``, ``line_profiler``, ``memory_profiler`` y ``Scalene``),
       E/S de archivos grandes y predicción de tiempos con IA.
   * - 3 · Optimización
     - ``/optimizacion``
     - Código redundante eliminado y refactorización, comparando la versión
       inicial con la final.
   * - 4 · Pruebas
     - ``/pruebas``
     - Ejecuta y muestra la suite de pruebas.
   * - 5 · Calidad
     - ``/calidad``
     - Ruff, cobertura de las pruebas y condiciones de calidad.
   * - 6 · Documentación
     - ``/documentacion``
     - Esta documentación, generada con Sphinx.

La documentación interactiva de la API que genera FastAPI está en
http://127.0.0.1:8000/docs.

Puertos utilizados
------------------

* ``8000``: aplicación web y API.
* ``8081``: servidor de SnakeViz, que se inicia solo la primera vez que se
  abre el perfil de un algoritmo en la ventana Análisis y se cierra junto con
  la aplicación.

Documentación
-------------

Al arrancar, la aplicación genera esta documentación si todavía no existe.
Para regenerarla se puede usar el botón de la ventana Documentación o el
comando:

.. code-block:: bash

   python -m sphinx -b html docs docs/_build/html

Estructura del proyecto
-----------------------

.. code-block:: text

   main.py            punto de entrada (uvicorn)
   api/               capa web: rutas FastAPI, modelos pydantic, SnakeViz
   web/               HTML, CSS y JavaScript de las ventanas
   rutas/             lógica pura (sin web): grafo, algoritmos, caché,
                      mediciones, perfilado, concurrencia y E/S
   rutas/algoritmos/  BFS, Dijkstra, A* y utilidades comunes
   perfiles/          archivos .prof generados por cProfile (SnakeViz)
   tests/             pruebas unittest / pytest / timeit
   docs/              fuentes de esta documentación (Sphinx)
   pyproject.toml     configuración de Ruff y cobertura
   pytest.ini         configuración de pytest (incluye doctest)
