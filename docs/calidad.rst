Análisis de calidad
===================

La ventana **Calidad** (``/calidad``, endpoints ``POST /api/calidad/lint`` y
``POST /api/calidad/cobertura``) y el pipeline de integración continua
(``.github/workflows/ci.yml``) aplican las mismas comprobaciones.

Herramienta de análisis estático
--------------------------------

Se usa `Ruff <https://docs.astral.sh/ruff/>`_ (alternativa moderna y rápida a
Flake8 y Pylint). Su configuración está en ``pyproject.toml`` y activa:

* ``E``, ``W``: estilo (pycodestyle).
* ``F``: errores (imports sin usar, variables no definidas).
* ``I``: orden de los imports.
* ``B``: errores probables (flake8-bugbear).
* ``UP``, ``C4``, ``SIM``: sintaxis moderna y simplificaciones.
* ``C90``: complejidad ciclomática máxima de 10 por función.

Además, ``ruff format --check`` verifica que el código tenga el formato
estándar.

Condiciones de calidad
----------------------

El pipeline **falla** si ocurre cualquiera de estas situaciones:

1. ``ruff check .`` encuentra al menos un problema.
2. ``ruff format --check .`` encuentra archivos sin formatear.
3. Alguna prueba automatizada no pasa.
4. La cobertura de las pruebas baja del mínimo (``fail_under`` en
   ``pyproject.toml``, actualmente 80 %).

Uso local
---------

.. code-block:: bash

   ruff check .                 # análisis estático
   ruff check . --fix           # corrige lo que se pueda automáticamente
   ruff format .                # da formato al código
   pytest --cov                 # pruebas + cobertura


API de la ventana
-----------------

.. automodule:: api.calidad_router
   :members:
