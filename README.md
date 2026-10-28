# Rutas en grafos: BFS, Dijkstra y A\*

Aplicación web hecha con **FastAPI** y HTML para construir un grafo
ponderado, buscar rutas con tres algoritmos (BFS, Dijkstra y A\*) y analizar
su eficiencia con mediciones reales.

## Requisitos e instalación

Python 3.12 o superior.

```bash
pip install -r requirements.txt
python main.py
```

Con eso se levanta todo. Abrir <http://127.0.0.1:8000>.

## Ventanas

| Ventana           | Dirección        | Contenido                                                        |
| ----------------- | ---------------- | ---------------------------------------------------------------- |
| 1 · Editor        | `/`              | Editor del grafo, búsqueda de rutas y comparación de algoritmos. |
| 2 · Análisis      | `/analisis`      | Benchmark y escalabilidad hasta 100.000 nodos, caché, concurrencia, perfilado (cProfile, line_profiler, Scalene), E/S e IA. |
| 3 · Optimización  | `/optimizacion`  | Código redundante, refactorización y herramientas de limpieza.   |
| 4 · Pruebas       | `/pruebas`       | Ejecuta y muestra la suite de pruebas.                           |
| 5 · Calidad       | `/calidad`       | Quality Gate y métricas de SonarQube Cloud.                      |
| 6 · Documentación | `/documentacion` | Referencia del código (Sphinx).                                 |

La documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>.

### Puertos

- `8000`: aplicación web y API.
- `8081`: servidor de SnakeViz. Se inicia solo al abrir el perfil de un
  algoritmo en la ventana Análisis y se cierra junto con la aplicación.

## Documentación

Hay dos documentaciones, versionadas en Git y publicadas juntas en GitHub Pages por `.github/workflows/docs.yml`:

| Documentación | Herramienta | Carpeta | Contenido |
| --- | --- | --- | --- |
| **Externa** (raíz del sitio) | MkDocs con Material | `documentacion/` y `mkdocs.yml` | Todo lo que explica el sistema: funcional, arquitectura, uso, diseño, API, pruebas, rendimiento, seguridad y mantenimiento. |
| **Interna** (`/interna/`) | Sphinx | `docs/` | Referencia de módulos, clases y funciones, generada de los *docstrings*. |

Cobertura de la documentación externa (los 9 puntos del enunciado):

| Contenido | Página (`documentacion/`) |
| --- | --- |
| Descripción funcional y requisitos | `funcional.md` |
| Arquitectura y diagrama de componentes | `arquitectura.md` |
| Instalación y ejecución | `uso.md` |
| Diseño técnico y decisiones | `algoritmos.md`, `decisiones.md`, `optimizacion.md`, `ia.md` |
| API y contratos | `api_rest.md` |
| Pruebas | `pruebas.md` |
| Rendimiento | `rendimiento.md` |
| Seguridad | `seguridad.md`, `calidad.md` |
| Mantenimiento y cómo correr los controles del CI en local | `mantenimiento.md` |

```bash
mkdocs serve                                           # externa en http://127.0.0.1:8001
mkdocs build --strict                                  # como en el CI
python -m sphinx -b html -q -W docs docs/_build/html   # interna
```

## Estructura

```text
main.py            punto de entrada (uvicorn)
api/               capa web: rutas FastAPI, modelos pydantic, SnakeViz
web/               HTML, CSS y JavaScript de las ventanas
rutas/             lógica pura (sin web): grafo, caché, mediciones,
                   perfilado, concurrencia y E/S
rutas/algoritmos/  BFS, Dijkstra, A* y utilidades comunes
perfiles/          archivos .prof generados por cProfile (SnakeViz)
tests/             pruebas unittest / pytest / timeit
documentacion/     documentación externa (MkDocs)
docs/              referencia interna del código (Sphinx)
mkdocs.yml         configuración de MkDocs
pyproject.toml     configuración de Ruff, mypy, Vulture y cobertura
sonar-project.properties  configuración de SonarQube Cloud
.github/workflows/ ci.yml (pipeline de CI) y docs.yml (publica la documentación)
pytest.ini         configuración de pytest (incluye doctest)
```

## Desarrollo

```bash
pytest                       # pruebas (incluye doctests)
pytest --cov                 # pruebas + cobertura (mínimo 80 %)
ruff check .                 # análisis estático
ruff format .                # formato (líneas de hasta 79 caracteres)
mypy                         # tipado (configurado en pyproject.toml)
pylint rutas api main.py --disable=all --enable=duplicate-code  # repetido
vulture                      # código muerto
bandit -r rutas api main.py -ll   # seguridad del código
pip-audit -r requirements.txt     # seguridad de las dependencias
```

Para regenerar la documentación a mano:

```bash
python -m sphinx -b html docs docs/_build/html
```

La app la genera sola al arrancar si todavía no existe.

## Decisiones de optimización

Una optimización solo se acepta si una medición muestra un problema real:
primero una versión clara y correcta, después `cProfile` para ubicar el
costo, la mejora y una nueva medición. Más detalle en
`documentacion/decisiones.md` y `documentacion/algoritmos.md`.

### Cola de prioridad en Dijkstra
En `rutas/algoritmos/comunes.py` Dijkstra usa `heapq` para obtener siempre el
nodo de menor costo. Esto da O((V+E) log V), frente a O(V²) de buscar el
mínimo recorriendo todos los nodos, y es lo que permite llegar a 100.000
nodos.

### Conjunto en lugar de lista para los nodos cerrados
`cerrados` es un `set`: preguntar `actual in cerrados` es O(1). Con una lista
sería O(n) por pregunta y el algoritmo se vuelve cuadrático. Está comprobado:
`regresion_rendimiento.patch` hace ese cambio y la mediana de Dijkstra pasa de
12,6 ms a 306 ms con 20.000 nodos (unas 24 veces más lento). El Performance
Gate del pipeline detecta justamente esa regresión.

### Un único bucle para Dijkstra y A\*
Pylint (`duplicate-code`) detectó el mismo bucle en ambos algoritmos. Ahora
existe `buscar_con_heap()` y A\* solo le pasa su heurística. Se midió que
Dijkstra queda dentro del ruido (±3 %) de la versión duplicada, y un cambio
futuro se hace en un solo lugar.

### BFS con un solo diccionario
BFS usa `collections.deque` (cola con O(1) en ambos extremos) y un único
diccionario de predecesores: que un nodo sea clave ya significa que fue
descubierto, así que no hace falta un segundo conjunto de visitados.

### Caché acotada
`CacheRutas` guarda el resultado por `(origen, destino)`, se vacía cuando
cambia la versión del grafo y conserva como máximo 2.048 entradas. Así no
devuelve rutas viejas ni crece sin límite.

### Sin paralelizar una sola búsqueda
Los hilos comparten el GIL y no aceleran trabajo de CPU; por eso solo se
paralelizan lotes de 10 consultas, y se compara secuencial, hilos y
procesos. Para archivos grandes se usa buffer al escribir y lectura por
lotes (`itertools.islice`), con memoria constante.

### Medir tiempo y memoria por separado
`rutas/mediciones.py` mide el tiempo en una corrida limpia y la memoria en
otra con `tracemalloc`, porque `tracemalloc` enlentece la ejecución y
falsearía el tiempo.

**Por qué importa:** quien modifique el código sabe qué decisiones no debe
deshacer sin volver a medir (escalabilidad) y por qué cada estructura es la
que es (mantenibilidad).

## Integración continua y SonarQube

El workflow `.github/workflows/ci.yml` corre en cada push a `main` y en cada
Pull Request hacia `main`. Está dividido en etapas; las independientes corren
en paralelo y la más costosa (rendimiento y memoria) solo corre si las demás
aprobaron:

| Control             | Herramienta                          | Criterio de rechazo                                  | Informe |
| ------------------- | ------------------------------------ | ---------------------------------------------------- | ------- |
| Pruebas             | pytest (+ doctest)                   | Una prueba falla                                     | `resultados.xml` |
| Cobertura           | coverage.py / pytest-cov             | Menos de 80 %                                        | `coverage.xml` |
| Análisis estático   | Ruff, Pylint, Vulture, SonarQube     | Cualquier hallazgo / Quality Gate                    | log, Sonar |
| Tipado              | mypy                                 | Función sin tipos o error de tipos                   | log |
| Complejidad         | Ruff (C90) y Radon                   | Función de rango C o peor (más de 10)                | `radon-cc.json`, `radon-mi.json` |
| Vulnerabilidades    | Bandit, pip-audit                    | Bandit media o alta; cualquier CVE en dependencias   | `bandit.json`, `pip-audit.json` |
| Secretos            | Gitleaks                             | Cualquier secreto en el historial                    | log |
| Dependencias        | Dependabot, `pip freeze` por corrida | (propone actualizaciones cada semana)                | `requirements-resuelto.txt` |
| Documentación       | MkDocs `--strict`, Sphinx `-W` y Lychee | Advertencia, enlace roto o enlace externo caído   | log |
| Benchmark           | Performance Gate                     | Mediana de Dijkstra con 100.000 nodos ≥ 500 ms       | resumen de la corrida |
| Memoria             | Memory Gate (`tracemalloc`)          | Pico de Dijkstra con 100.000 nodos > 32 MiB          | resumen de la corrida |
| Profiling de CPU    | cProfile                             | Informativo (no bloquea)                             | `perfiles/*.prof` |

El job **Resultado final** es Aprobado solo si todas las etapas terminaron en
`success`. El tiempo varía con la máquina (se usa la mediana y un umbral con
margen); la memoria con `tracemalloc` es determinista (15,2 MiB medidos, límite
32 MiB).

Los mismos controles se pueden correr en local:

```bash
ruff check . && ruff format --check . && mypy
vulture && bandit -r rutas api main.py -ll
radon cc rutas api main.py -a -s -nb
pip-audit -r requirements.txt
mkdocs build --strict
python -m sphinx -b html -q -W docs docs/_build/html
pytest --cov --cov-report=term-missing   # falla si baja del 80 %
python -m rutas.performance_gate
python -m rutas.memory_gate
```

Política de seguridad: Bandit bloquea severidad media o alta; pip-audit
bloquea cualquier vulnerabilidad conocida; Gitleaks bloquea cualquier
secreto. Los hallazgos de severidad baja se aceptan y quedan justificados, con
los falsos positivos y las medidas correctivas, en `documentacion/calidad.md` y `documentacion/seguridad.md`.

Para activarlo en un repositorio nuevo:

1. Importar el repositorio en SonarQube Cloud y copiar la clave de la
   organización y del proyecto a `sonar-project.properties`.
2. Desactivar el *análisis automático* del proyecto en SonarQube Cloud.
3. Generar un token en SonarQube Cloud y guardarlo en GitHub como secret
   `SONAR_TOKEN` (Settings → Secrets and variables → Actions).
4. En GitHub, proteger la rama `main` exigiendo que pase el check `CI / Resultado final`
   antes de hacer merge. El check a exigir es **Resultado final**.

