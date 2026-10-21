Análisis de calidad
===================

La calidad se controla en dos lugares: el **pipeline de integración
continua** (``.github/workflows/ci.yml``), que ejecuta varias herramientas en
cada push y en cada Pull Request, y la ventana **Calidad** (``/calidad``), que
muestra el resultado de **SonarQube Cloud**.

Pasos del pipeline
------------------

El pipeline **falla** en cuanto un paso incumple su criterio:

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Paso
     - Qué verifica
     - Cuándo falla
   * - Arranque
     - Importa la aplicación y consulta ``/``.
     - La aplicación no inicia o no responde.
   * - Ruff
     - Errores probables, imports sin usar, complejidad (máximo 10 por
       función), código comentado y formato.
     - Cualquier hallazgo o archivo sin formatear.
   * - mypy
     - Tipos en todas las funciones.
     - Una función sin tipos o un error de tipos.
   * - Vulture y Pylint
     - Código muerto y bloques repetidos entre archivos.
     - Cualquier elemento sin usar o bloque repetido.
   * - Bandit
     - Vulnerabilidades en el código propio (ver más abajo).
     - Severidad media o alta.
   * - pip-audit
     - Dependencias con vulnerabilidades conocidas (CVE).
     - Cualquier vulnerabilidad conocida.
   * - pytest
     - Todas las pruebas y la cobertura (``coverage.xml``).
     - Una prueba falla o la cobertura baja del ``fail_under`` de
       ``pyproject.toml`` (80 %). El resumen de pruebas queda en la página de
       la corrida.
   * - SonarQube Cloud
     - Quality Gate sobre el código nuevo.
     - El Quality Gate no se cumple.

Los resultados de pruebas y cobertura se guardan como evidencia (artefacto
``resultados``) en cada corrida.

SonarQube Cloud
---------------

`SonarQube Cloud <https://sonarcloud.io>`_ analiza el código y detecta
**bugs**, **vulnerabilidades**, **puntos críticos de seguridad** (*security
hotspots*), **code smells** (código difícil de mantener) y **duplicación**, y
mide la cobertura de las pruebas. El **Quality Gate** es el conjunto de
condiciones que debe cumplir el código nuevo; si falla, el pipeline falla
(``sonar.qualitygate.wait=true``).

Configuración:

* ``sonar-project.properties``: organización, clave del proyecto, carpetas de
  código y de pruebas, y la ruta de ``coverage.xml``. Las claves no son
  secretas.
* Secret ``SONAR_TOKEN`` en GitHub (Settings → Secrets and variables →
  Actions): el token no está en el repositorio. Sin él (por ejemplo, en Pull
  Requests desde forks) el paso de Sonar se omite.
* ``pyproject.toml``: ``relative_files = true`` hace que ``coverage.xml`` traiga
  rutas como ``api/app.py``, que es como SonarQube asocia la cobertura a los
  archivos del repositorio.
* En SonarQube Cloud hay que tener desactivado el *análisis automático*, que
  no admite cobertura y se pisa con el análisis desde el pipeline.

La ventana **Calidad** no analiza nada: consulta la API de SonarQube Cloud
(``GET /api/calidad/sonar``) y muestra el estado del Quality Gate, sus
condiciones y las métricas. Si el proyecto fuera privado, se define la variable
de entorno ``SONAR_TOKEN``.

Qué agrega SonarQube respecto de las demás herramientas
-------------------------------------------------------

Las herramientas locales dan respuesta inmediata y bloquean problemas antes
del push. SonarQube aporta lo que ellas no tienen: historial, Quality Gate
sobre el código nuevo, calificaciones (A a E) de fiabilidad, seguridad y
mantenibilidad, y un panel para ver la evolución. Hay cierto solapamiento a
propósito (por ejemplo, duplicación y code smells): cada herramienta ve el
mismo código con reglas distintas.

Seguridad
---------

* **Bandit** analiza el código en busca de patrones inseguros. Criterio: el
  pipeline falla con severidad **media o alta**. Las de severidad **baja** se
  aceptan por estos motivos:

  * ``B404`` y ``B603`` (``subprocess``): los comandos son listas fijas y no
    usan ``shell``; nunca incluyen texto del usuario.
  * ``B311`` (``random``): se usa para generar grafos y consultas de prueba,
    no para nada criptográfico.

  El único hallazgo medio (``B314``) era el análisis del XML de ``pytest``
  con ``xml.etree``; se resolvió usando ``defusedxml``.
* **pip-audit** compara las dependencias de ``requirements.txt`` con la base
  de vulnerabilidades conocidas. Criterio: falla con cualquier vulnerabilidad.

Configuración de Ruff
---------------------

Su configuración está en ``pyproject.toml`` y activa:

* ``E``, ``W``: estilo (pycodestyle).
* ``F``: errores (imports sin usar, variables no definidas).
* ``I``: orden de los imports.
* ``B``: errores probables (flake8-bugbear).
* ``UP``, ``C4``, ``SIM``: sintaxis moderna y simplificaciones.
* ``C90``: complejidad ciclomática máxima de 10 por función.
* ``ERA``: código comentado.

Uso local
---------

.. code-block:: bash

   ruff check .                 # análisis estático
   ruff format .                # da formato al código
   mypy                         # tipos
   vulture                      # código muerto
   bandit -r rutas api main.py -ll
   pip-audit -r requirements.txt
   pytest --cov --cov-report=xml

API de la ventana
-----------------

.. automodule:: api.calidad_router
   :members:
