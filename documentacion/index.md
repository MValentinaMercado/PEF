# Rutas en grafos: BFS, Dijkstra y A\*

Aplicación web hecha con **FastAPI** para construir un grafo ponderado, buscar rutas con tres algoritmos (BFS, Dijkstra y A\*) y analizar su eficiencia con mediciones reales. Esta es su documentación externa: explica qué hace el sistema, cómo se usa, cómo está diseñado y cómo se mantiene.

## Contenido

| # | Sección | Qué responde |
|---|---------|--------------|
| 1 | [Descripción funcional](funcional.md) | Qué problema resuelve, alcance y requisitos. |
| 2 | [Arquitectura](arquitectura.md) | Módulos, responsabilidades, dependencias y diagrama de componentes. |
| 3 | [Instalación y uso](uso.md) | Dependencias, comandos y puertos. |
| 4 | Diseño técnico: [algoritmos](algoritmos.md), [decisiones](decisiones.md), [optimización](optimizacion.md) e [IA](ia.md) | Estructuras de datos, algoritmos y por qué se implementaron así. |
| 5 | [API REST](api_rest.md) | Entradas, salidas, errores y ejemplos. |
| 6 | [Pruebas](pruebas.md) | Estrategia, casos y resultados. |
| 7 | [Rendimiento](rendimiento.md) | Benchmarks, profiling, complejidad y memoria. |
| 8 | [Seguridad](seguridad.md) | Riesgos, dependencias vulnerables y medidas correctivas. |
| 9 | [Mantenimiento](mantenimiento.md) y [calidad](calidad.md) | Cómo contribuir, correr los controles del CI en local y resolver fallos del pipeline. |

## Documentación interna

La referencia de módulos, clases y funciones se genera con Sphinx a partir de los *docstrings* y se publica junto a este sitio: <a href="interna/">Referencia del código</a>. Por qué se usan dos herramientas: [Mantenimiento](mantenimiento.md#por-que-dos-herramientas).

## Para empezar

```bash
pip install -r requirements.txt
python main.py        # aplicación en http://127.0.0.1:8000
mkdocs serve          # esta documentación en http://127.0.0.1:8001
```
