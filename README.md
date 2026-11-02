# Rutas en grafos: BFS, Dijkstra y A\*

Aplicación web desarrollada con **FastAPI** para construir grafos, buscar rutas mediante **BFS, Dijkstra y A\*** y analizar su rendimiento, escalabilidad y calidad.

El proyecto incluye pruebas automatizadas, cobertura de código, análisis estático, controles de seguridad, benchmarks, perfilado, documentación externa e interna y un pipeline de Integración Continua (CI) con GitHub Actions.

## Documentación

La documentación del proyecto está publicada mediante **GitHub Pages**.

**Documentación externa:** explica el sistema desde el punto de vista funcional, técnico y de mantenimiento.

**Documentación interna:** referencia detallada de módulos, clases y funciones generada con Sphinx a partir de los docstrings.

### Acceso

- **Documentación externa:** disponible desde la página de GitHub Pages del proyecto.
- **Documentación interna:** disponible dentro de la sección `/interna/` de GitHub Pages.

La publicación se realiza automáticamente mediante:

```text
.github/workflows/docs.yml
```

La documentación externa está construida con **MkDocs + Material** y utiliza los contenidos de:

```text
documentacion/
mkdocs.yml
```

La documentación interna está construida con **Sphinx** a partir de:

```text
docs/
```

## Funcionalidades

La aplicación permite:

- Crear y editar grafos.
- Buscar rutas entre nodos.
- Ejecutar BFS, Dijkstra y A\*.
- Comparar algoritmos.
- Analizar rendimiento y escalabilidad.
- Ejecutar benchmarks con grafos de hasta 100.000 nodos.
- Analizar concurrencia.
- Medir tiempo y memoria.
- Realizar perfilado con `cProfile`, `line_profiler` y Scalene.
- Analizar código redundante y oportunidades de optimización.
- Ejecutar la suite de pruebas.
- Consultar el estado de los controles de calidad.
- Consultar la documentación de la API mediante FastAPI.

## Requisitos

Se requiere:

- Python 3.12 o superior.
- Git.

Se recomienda utilizar un entorno virtual.

## Instalación

Clonar el repositorio:

```bash
git clone https://github.com/MValentinaMercado/PEF.git
cd PEF
```

Crear y activar el entorno virtual.

En Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

Iniciar la aplicación:

```bash
python main.py
```

La aplicación queda disponible en:

```text
http://127.0.0.1:8000
```

La documentación interactiva de la API de FastAPI está disponible en:

```text
http://127.0.0.1:8000/docs
```

## Ventanas de la aplicación

| Ventana       | Ruta             | Contenido                                                        |
| ------------- | ---------------- | ---------------------------------------------------------------- |
| Editor        | `/`              | Editor del grafo, búsqueda de rutas y comparación de algoritmos. |
| Análisis      | `/analisis`      | Benchmark, escalabilidad, caché, concurrencia y perfilado.       |
| Optimización  | `/optimizacion`  | Análisis de código redundante y refactorización.                 |
| Pruebas       | `/pruebas`       | Ejecución y visualización de la suite de pruebas.                |
| Calidad       | `/calidad`       | Quality Gate de SonarQube Cloud y estado del CI.                 |
| Documentación | `/documentacion` | Referencia interna del código mediante Sphinx.                   |

## Puertos

| Puerto | Uso                                                  |
| ------ | ---------------------------------------------------- |
| `8000` | Aplicación web y API.                                |
| `8081` | Servidor de SnakeViz utilizado durante el perfilado. |

## Estructura del proyecto

```text
PEF/
├── api/                    Capa web y rutas FastAPI
├── docs/                   Documentación interna con Sphinx
├── documentacion/          Documentación externa con MkDocs
├── perfiles/               Archivos generados por cProfile
├── rutas/                  Lógica de grafos, algoritmos y mediciones
├── tests/                  Pruebas automatizadas
├── web/                    HTML, CSS y JavaScript
├── .github/
│   └── workflows/
│       ├── ci.yml          Pipeline de Integración Continua
│       └── docs.yml        Publicación de documentación
├── main.py                 Punto de entrada de la aplicación
├── mkdocs.yml              Configuración de MkDocs
├── pyproject.toml          Configuración de herramientas de calidad
├── pytest.ini              Configuración de pytest
├── requirements.txt        Dependencias del proyecto
└── sonar-project.properties
```

## Algoritmos

El proyecto implementa tres algoritmos principales:

### BFS

Breadth-First Search utiliza una cola para recorrer el grafo por niveles. Es apropiado para encontrar caminos mínimos en cantidad de aristas cuando el grafo no utiliza pesos relevantes.

### Dijkstra

Dijkstra utiliza una cola de prioridad implementada mediante `heapq`.

La implementación tiene complejidad:

```text
O((V + E) log V)
```

Esto permite trabajar con grafos de gran tamaño.

### A\*

A\* utiliza una heurística junto con una cola de prioridad para orientar la búsqueda hacia el destino.

La implementación comparte la lógica común de búsqueda con Dijkstra y permite evitar duplicación de código.

## Optimizaciones

Las optimizaciones se incorporaron a partir de mediciones y no solamente de suposibilidad teórica.

Entre las principales decisiones se encuentran:

- Uso de `heapq` en Dijkstra y A\*.
- Uso de `set` para los nodos cerrados.
- Uso de `deque` en BFS.
- Caché acotada para rutas calculadas.
- Paralelización únicamente para lotes de consultas.
- Uso de procesos cuando el trabajo puede beneficiarse del paralelismo de CPU.
- Separación de mediciones de tiempo y memoria.
- Refactorización de código común entre Dijkstra y A\*.

Las decisiones técnicas y sus mediciones están documentadas en:

```text
documentacion/algoritmos.md
documentacion/decisiones.md
documentacion/optimizacion.md
```

## Pruebas y cobertura

La suite de pruebas se ejecuta mediante `pytest`.

Ejecutar las pruebas:

```bash
pytest
```

Ejecutar las pruebas con cobertura:

```bash
pytest --cov
```

El proyecto utiliza un umbral mínimo de cobertura del **80 %**.

## Controles de calidad

El proyecto utiliza diferentes herramientas para controlar la calidad del código:

```bash
ruff check .
ruff format --check .
mypy
vulture
```

También se utilizan:

```bash
pylint rutas api main.py --disable=all --enable=duplicate-code
radon cc rutas api main.py -a -s -nb
```

## Seguridad

Se utilizan herramientas específicas para analizar el código y las dependencias:

```bash
bandit -r rutas api main.py -ll
pip-audit -r requirements.txt
```

También se utiliza **Gitleaks** dentro del pipeline de CI para detectar secretos.

Los controles y las decisiones relacionadas con seguridad están documentados en:

```text
documentacion/seguridad.md
documentacion/calidad.md
```

## Integración Continua

El proyecto utiliza **GitHub Actions** para ejecutar automáticamente los controles de calidad.

El workflow principal se encuentra en:

```text
.github/workflows/ci.yml
```

Entre los controles ejecutados se encuentran:

- Pruebas automatizadas.
- Cobertura.
- Ruff.
- Pylint.
- mypy.
- Vulture.
- Radon.
- Bandit.
- pip-audit.
- Gitleaks.
- SonarQube Cloud.
- Validación de documentación.
- Verificación de enlaces.
- Performance Gate.
- Memory Gate.
- Perfilado de CPU.

El resultado final del pipeline determina si todos los controles obligatorios fueron satisfactorios.

## Documentación local

Para ejecutar la documentación externa de MkDocs localmente:

```bash
mkdocs serve -a 127.0.0.1:8001
```

La documentación estará disponible en:

```text
http://127.0.0.1:8001
```

Para verificar que la documentación puede construirse correctamente:

```bash
mkdocs build --strict
```

Para generar la documentación interna con Sphinx:

```bash
python -m sphinx -b html -q -W docs docs/_build/html
```

## Controles de rendimiento

El proyecto incorpora controles específicos para evitar regresiones de rendimiento.

Ejecutar el Performance Gate:

```bash
python -m rutas.performance_gate
```

Ejecutar el Memory Gate:

```bash
python -m rutas.memory_gate
```

Los benchmarks permiten comprobar el comportamiento de los algoritmos sobre grafos de gran tamaño.

## SonarQube Cloud

El proyecto incorpora análisis mediante SonarQube Cloud.

La configuración se encuentra en:

```text
sonar-project.properties
```

El pipeline utiliza el secreto:

```text
SONAR_TOKEN
```

para autenticarse durante el análisis.

## Desarrollo

Los principales controles utilizados durante el desarrollo pueden ejecutarse localmente mediante:

```bash
ruff check .
ruff format --check .
mypy
vulture
bandit -r rutas api main.py -ll
radon cc rutas api main.py -a -s -nb
pip-audit -r requirements.txt
mkdocs build --strict
python -m sphinx -b html -q -W docs docs/_build/html
pytest --cov
python -m rutas.performance_gate
python -m rutas.memory_gate
```

Antes de realizar un commit se recomienda ejecutar los controles relevantes y verificar que el árbol de trabajo esté limpio:

```bash
git status
```

## Estado del proyecto

El proyecto integra:

- Aplicación web con FastAPI.
- Algoritmos BFS, Dijkstra y A\*.
- Pruebas automatizadas.
- Cobertura de código.
- Análisis estático.
- Análisis de seguridad.
- Control de dependencias.
- Análisis de calidad con SonarQube Cloud.
- Benchmarks y controles de rendimiento.
- Perfilado.
- Documentación externa con MkDocs.
- Documentación interna con Sphinx.
- Integración Continua con GitHub Actions.
- Publicación automática de documentación mediante GitHub Pages.
