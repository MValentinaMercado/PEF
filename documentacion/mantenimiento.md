# Mantenimiento

## Dónde está la documentación

Hay dos documentaciones con herramientas distintas. Ambas viven **en el repositorio de Git** y se publican juntas como un solo sitio en **GitHub Pages** con el workflow `.github/workflows/docs.yml` en cada cambio de `main`:

| | Externa | Interna |
|---|---|---|
| Herramienta | MkDocs con el tema Material | Sphinx |
| Carpeta | `documentacion/` (Markdown) y `mkdocs.yml` | `docs/` (reStructuredText) y `docs/conf.py` |
| Qué contiene | Qué hace el sistema, cómo se instala y se usa, arquitectura, decisiones, API, pruebas, seguridad y mantenimiento | Referencia de módulos, clases y funciones, generada de los *docstrings* |
| Dirección en el sitio | raíz | `/interna/` |

- **Acceso y control:** quien puede leer o escribir la documentación es quien tiene ese permiso sobre el repositorio. Los cambios entran por Pull Request con revisión y quedan en el historial de Git (quién, cuándo y por qué).
- **Colaboración:** cada integrante edita su rama y la documentación se revisa igual que el código.
- **Actualización:** la referencia interna se genera de los *docstrings* (`sphinx.ext.autodoc`) y los ejemplos `>>>` se ejecutan como pruebas, así que no se desactualiza en silencio. El pipeline construye ambos sitios en modo estricto (`mkdocs build --strict` y `sphinx -W`): un enlace roto o una referencia inexistente hacen fallar la integración.
- **Visibilidad del sitio:** en un repositorio privado, GitHub Pages es público salvo en los planes Enterprise. Si la documentación debe quedar privada, se puede descargar el artefacto de la corrida o publicar con Read the Docs.

## Por qué dos herramientas

**MkDocs** es lo más simple para guías escritas a mano: Markdown, un único `mkdocs.yml` y un tema (Material) que resuelve navegación, búsqueda y diagramas Mermaid. Lo usamos para la documentación externa porque quien la lee no es quien programa el módulo y se edita como texto común.

**Sphinx** se usa para lo interno porque lee los *docstrings* directamente (`autodoc` y `napoleon`) y ejecuta los ejemplos con `doctest`: la referencia del código se actualiza cuando cambia el código. MkDocs necesitaría un plugin (`mkdocstrings`) para hacer lo mismo.

Se descartaron Confluence, Notion y GitBook: son colaborativos pero no viven junto al código ni se construyen en el pipeline.

Para activar la publicación en un repositorio nuevo: *Settings → Pages → Source: GitHub Actions*.

## Ejecutar localmente los controles del CI

Todos los controles del pipeline se pueden ejecutar en la computadora con los mismos comandos. Instalar una vez las dependencias y después, desde la raíz del proyecto:

```bash
pip install -r requirements.txt
```

| Etapa del CI             | Comando local                                                                                                          | Falla si                                      |
|--------------------------|------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| Secretos                 | `gitleaks detect --source .` (programa aparte)                                                                         | Hay un secreto en el historial                |
| Estilo y errores         | `ruff check .` y `ruff format --check .`                                                                               | Cualquier hallazgo                            |
| Tipos                    | `mypy`                                                                                                                 | Error de tipos                                |
| Código muerto y repetido | `vulture` y `pylint rutas api main.py --disable=all --enable=duplicate-code --score=n`                                 | Cualquier hallazgo                            |
| Complejidad              | `radon cc rutas api main.py -a -s -nb` (informe) y `radon cc rutas api main.py -nc` (debe no imprimir nada)            | Función de rango C o peor                     |
| Seguridad del código     | `bandit -r rutas api main.py -ll`                                                                                      | Severidad media o alta                        |
| Pruebas y cobertura      | `pytest --cov --cov-report=term-missing`                                                                               | Una prueba falla o la cobertura baja del 90 % |
| Dependencias             | `pip-audit -r requirements.txt`                                                                                        | Vulnerabilidad conocida                       |
| Documentación externa    | `mkdocs build --strict`                                                                                                | Advertencia o enlace interno roto             |
| Enlaces externos         | `lychee --exclude 127.0.0.1 documentacion README.md` (programa aparte, opcional)                              | Enlace externo caído                          |
| Referencia interna       | `python -m sphinx -b html -q -W docs docs/_build/html`                                                                 | Advertencia o referencia rota                 |
| Benchmark                | `python -m rutas.performance_gate`                                                                                     | Mediana de Dijkstra \>= 500 ms                |
| Memoria                  | `python -m rutas.memory_gate`                                                                                          | Pico de Dijkstra \> 32 MiB                    |
| Profiling de CPU         | Ver el comando en [Rendimiento](rendimiento.md) (deja los `.prof` en `perfiles/`)                                                      | No bloquea (informativo)                      |

SonarQube Cloud solo se ejecuta en el pipeline (necesita el secret `SONAR_TOKEN`); en local se ven sus resultados en la ventana Calidad. El tiempo depende de la máquina: si el Performance Gate falla solo en local, repetirlo antes de investigar.

## Cómo contribuir

1.  Crear una rama desde `main`.
2.  Hacer el cambio. Si modifica el comportamiento, agregar o ajustar la prueba y actualizar la documentación que corresponda (ver la tabla de abajo).
3.  Ejecutar localmente los controles de la sección anterior.
4.  Abrir un Pull Request hacia `main`. El pipeline corre solo.
5.  Pedir revisión. Se integra únicamente si **Resultado final** aprobó.

| Si el cambio...                                         | Actualizar                                                                       |
|---------------------------------------------------------|----------------------------------------------------------------------------------|
| agrega o cambia un endpoint                             | [API REST](api_rest.md) y la prueba en `tests/test_api.py`                                    |
| agrega un módulo o cambia una dependencia entre módulos | [Arquitectura](arquitectura.md) (y `docs/referencia.rst` si el módulo debe figurar en la referencia) |
| cambia una estructura de datos o un algoritmo           | [Algoritmos y estructuras de datos](algoritmos.md) y [Decisiones de diseño y optimización](decisiones.md)                                                      |
| es una optimización                                     | [Decisiones de diseño y optimización](decisiones.md) (qué, por qué y cómo se verificó) y los resultados de [Rendimiento](rendimiento.md) |
| cambia un umbral o agrega un control                    | [Análisis de calidad](calidad.md), la tabla de umbrales de [Decisiones de diseño y optimización](decisiones.md) y `.github/workflows/ci.yml`     |
| incorpora una excepción de seguridad                    | [Análisis de calidad](calidad.md) (con el motivo) y [Seguridad](seguridad.md)                                          |

## Resolver fallos del pipeline

El resumen de la corrida muestra qué etapa falló, y cada etapa deja sus informes como artefactos (`evidencias-*`).

| Falla                      | Causa probable                                               | Qué hacer                                                                                          |
|----------------------------|--------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Ruff o formato             | Estilo o error básico                                        | `ruff check . --fix` y `ruff format .`; revisar el resto a mano.                                   |
| mypy                       | Función sin tipos o tipo incorrecto                          | Agregar o corregir los tipos que indica el mensaje.                                                |
| Radon o Ruff (complejidad) | Función con demasiados caminos                               | Dividirla en funciones más chicas; no subir el límite.                                             |
| Pylint (duplicate-code)    | Código repetido entre módulos                                | Extraer la parte común (como `buscar_con_heap`).                                                   |
| Bandit                     | Patrón inseguro de severidad media o alta                    | Corregirlo; si es un falso positivo, documentarlo en [Análisis de calidad](calidad.md).                                    |
| Pruebas                    | Una prueba falla                                             | `pytest -x` en local; abrir `resultados.xml` del artefacto.                                        |
| Cobertura                  | Código nuevo sin pruebas                                     | `pytest --cov --cov-report=term-missing` muestra las líneas sin cubrir.                            |
| pip-audit                  | Dependencia con vulnerabilidad                               | Subir su versión en `requirements.txt`; ver `pip-audit.json`.                                      |
| Gitleaks                   | Secreto en el repositorio                                    | Revocarlo y generar uno nuevo (borrarlo no alcanza). Ver [Seguridad](seguridad.md).                              |
| MkDocs                     | Enlace a una página o ancla que no existe                    | Ejecutar `mkdocs build --strict` y leer la advertencia.                                            |
| Lychee                     | Enlace externo caído                                         | Corregir la URL o quitar el enlace.                                                                |
| Sphinx                     | Título mal subrayado, referencia o enlace roto               | Ejecutar el comando de la tabla anterior y leer la advertencia.                                    |
| Performance Gate           | Regresión de tiempo (por ejemplo lista en lugar de conjunto) | Perfilar con `cProfile` y revisar la estructura de datos del cambio; no subir el umbral sin medir. |
| Memory Gate                | Pico de memoria mayor (copias, estructuras que crecen)       | Revisar qué se guarda por consulta; `memory_profiler` indica la línea.                             |
| SonarQube (Quality Gate)   | Problema en el código nuevo                                  | Abrir el proyecto en SonarQube Cloud y corregir lo que marca.                                      |
| Resultado final            | Otra etapa falló o no corrió                                 | Ver la etapa fallida en el resumen; esta etapa no se arregla sola.                                 |

## Configuración del repositorio

- Secret `SONAR_TOKEN` en *Settings → Secrets and variables → Actions*.
- Protección de `main` (*Settings → Branches*): exigir Pull Request y el check **CI / Resultado final**.
- *Settings → Pages → Source: GitHub Actions* para publicar la documentación.
- Dependabot (`.github/dependabot.yml`) propone semanalmente las actualizaciones de Python y de las acciones.
