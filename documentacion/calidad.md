# Análisis de calidad

La calidad se controla en dos lugares: el **pipeline de integración continua** (`.github/workflows/ci.yml`), que ejecuta varias herramientas en cada push y en cada Pull Request, y la ventana **Calidad** (`/calidad`), que muestra el resultado de **SonarQube Cloud**.

## Pasos del pipeline

El pipeline se organiza en **etapas** (jobs). Las que no dependen entre sí corren en paralelo y las mediciones costosas solo se ejecutan si las anteriores aprobaron:

1.  `secretos`: Gitleaks.
2.  `estatica`: Ruff, mypy, Vulture, Pylint, Radon y Bandit.
3.  [Pruebas y perfilado](pruebas.md): arranque, pytest con cobertura y SonarQube Cloud.
4.  `seguridad_y_docs`: pip-audit, MkDocs (sitio externo y enlaces) y Sphinx (referencia interna).
5.  [Rendimiento](rendimiento.md): Performance Gate, Memory Gate y profiling de CPU (necesita que 1 a 4 hayan aprobado).
6.  `resultado`: **Resultado final**, Aprobado o Rechazado. Es el check que debe exigir la protección de la rama `main`.

Cada paso **falla** en cuanto incumple su criterio:

| Paso             | Qué verifica                                                                                                                          | Cuándo falla                                                                                                                                                                  |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Arranque         | Importa la aplicación y consulta `/`.                                                                                                 | La aplicación no inicia o no responde.                                                                                                                                        |
| Ruff             | Errores probables, imports sin usar, complejidad (máximo 10 por función), código comentado y formato.                                 | Cualquier hallazgo o archivo sin formatear.                                                                                                                                   |
| mypy             | Tipos en todas las funciones.                                                                                                         | Una función sin tipos o un error de tipos.                                                                                                                                    |
| Vulture y Pylint | Código muerto y bloques repetidos entre archivos.                                                                                     | Cualquier elemento sin usar o bloque repetido.                                                                                                                                |
| Bandit           | Vulnerabilidades en el código propio (ver más abajo).                                                                                 | Severidad media o alta.                                                                                                                                                       |
| Gitleaks         | Secretos (tokens, claves, contraseñas) en todo el historial.                                                                          | Cualquier secreto encontrado.                                                                                                                                                 |
| Radon            | Complejidad ciclomática por función e índice de mantenibilidad por archivo.                                                           | Una función de rango C o peor (complejidad mayor que 10) o un archivo con mantenibilidad de rango C.                                                                          |
| pip-audit        | Dependencias con vulnerabilidades conocidas (CVE).                                                                                    | Cualquier vulnerabilidad conocida.                                                                                                                                            |
| MkDocs | El sitio se construye con `--strict` (enlaces y referencias internas válidos) y los enlaces externos responden (Lychee; se ignoran las direcciones `127.0.0.1` de los ejemplos). | Cualquier advertencia, enlace roto o enlace externo caído. |
| Sphinx | La referencia interna se construye con `-W`. | Cualquier advertencia o referencia rota. |
| pytest           | Todas las pruebas y la cobertura (`coverage.xml`).                                                                                    | Una prueba falla o la cobertura baja del `fail_under` de `pyproject.toml` (80 %). El resumen de pruebas queda en la página de la corrida.                                     |
| SonarQube Cloud  | Quality Gate sobre el código nuevo.                                                                                                   | El Quality Gate no se cumple.                                                                                                                                                 |
| Performance Gate | Mediana de Dijkstra con 100.000 nodos (`rutas/performance_gate.py`).                                                                  | Mediana de 500 ms o más. Con el cambio de `regresion_rendimiento.patch` (lista en vez de conjunto) la mediana sube unas 24 veces en un grafo de 20.000 nodos y el gate falla. |
| Memory Gate      | Pico de memoria de Dijkstra con 100.000 nodos, medido con `tracemalloc` (`rutas/memory_gate.py`).                                     | Más de 32 MiB (el pico medido es de 15,2 MiB y es idéntico en cada corrida).                                                                                                  |
| Profiling de CPU | `cProfile` sobre los tres algoritmos; deja un `.prof` por algoritmo y un resumen.                                                     | Informativo, no bloquea: el bloqueo por CPU lo hace el Performance Gate.                                                                                                      |

Cada etapa guarda sus informes como artefactos de la corrida: `evidencias-estatica` (`bandit.json`, `radon-*.json`), `evidencias-pruebas` (`resultados.xml`, `coverage.xml`), `evidencias-seguridad-docs` (`pip-audit.json`, versiones exactas instaladas y resultado de los enlaces) y `evidencias-rendimiento` (perfiles `.prof`).

Los controles de tiempo y de memoria no se tratan igual: el tiempo varía con la máquina, así que se usa la **mediana** de varias corridas y un umbral con margen; la memoria medida con `tracemalloc` es determinista, por eso alcanza una sola medición con un límite del doble de lo observado.

## SonarQube Cloud

[SonarQube Cloud](https://sonarcloud.io) analiza el código y detecta **bugs**, **vulnerabilidades**, **puntos críticos de seguridad** (*security hotspots*), **code smells** (código difícil de mantener) y **duplicación**, y mide la cobertura de las pruebas. El **Quality Gate** es el conjunto de condiciones que debe cumplir el código nuevo; si falla, el pipeline falla (`sonar.qualitygate.wait=true`).

Configuración:

- `sonar-project.properties`: organización, clave del proyecto, carpetas de código y de pruebas, y la ruta de `coverage.xml`. Las claves no son secretas.
- Secret `SONAR_TOKEN` en GitHub (Settings → Secrets and variables → Actions): el token no está en el repositorio. Sin él (por ejemplo, en Pull Requests desde forks) el paso de Sonar se omite.
- `pyproject.toml`: `relative_files = true` hace que `coverage.xml` traiga rutas como `api/app.py`, que es como SonarQube asocia la cobertura a los archivos del repositorio.
- En SonarQube Cloud hay que tener desactivado el *análisis automático*, que no admite cobertura y se pisa con el análisis desde el pipeline.

La ventana **Calidad** no analiza nada: consulta la API de SonarQube Cloud (`GET /api/calidad/sonar`) y muestra el estado del Quality Gate, sus condiciones y las métricas. Si el proyecto fuera privado, se define la variable de entorno `SONAR_TOKEN`.

## Qué agrega SonarQube respecto de las demás herramientas

Las herramientas locales dan respuesta inmediata y bloquean problemas antes del push. SonarQube aporta lo que ellas no tienen: historial, Quality Gate sobre el código nuevo, calificaciones (A a E) de fiabilidad, seguridad y mantenibilidad, y un panel para ver la evolución. Hay cierto solapamiento a propósito (por ejemplo, duplicación y code smells): cada herramienta ve el mismo código con reglas distintas.

## Seguridad

- **Bandit** analiza el código en busca de patrones inseguros. Criterio: el pipeline falla con severidad **media o alta**. Las de severidad **baja** se aceptan por estos motivos:

  - `B404` y `B603` (`subprocess`): los comandos son listas fijas y no usan `shell`; nunca incluyen texto del usuario.
  - `B311` (`random`): se usa para generar grafos y consultas de prueba, no para nada criptográfico.

  El único hallazgo medio (`B314`) era el análisis del XML de `pytest` con `xml.etree`; se resolvió usando `defusedxml`.

- **pip-audit** compara las dependencias de `requirements.txt` con la base de vulnerabilidades conocidas. Criterio: falla con cualquier vulnerabilidad.

- **Gitleaks** busca secretos en todo el historial. Criterio: falla con cualquier hallazgo.

- **Dependabot** propone cada semana actualizaciones de las dependencias de Python y de las acciones del pipeline.

Informes: `bandit.json` y `pip-audit.json` (JSON) y la salida legible de cada paso en el log de la corrida.

### Política de bloqueo

| Hallazgo                                   | Severidad    | Decisión                                                                                                    |
|--------------------------------------------|--------------|-------------------------------------------------------------------------------------------------------------|
| Secreto expuesto                           | Cualquiera   | Bloquea. Además hay que revocar la credencial: borrarla del código no alcanza porque queda en el historial. |
| Vulnerabilidad conocida en una dependencia | Cualquiera   | Bloquea hasta actualizar la versión.                                                                        |
| Bandit                                     | Media o alta | Bloquea.                                                                                                    |
| Bandit                                     | Baja         | No bloquea; debe quedar justificada en esta página.                                                         |

### Falsos positivos y excepciones

Toda excepción se registra aquí con su motivo; una alerta sin justificación se considera abierta.

| Regla          | Dónde                                                         | Motivo de la excepción                                                                              |
|----------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| `B404`, `B603` | `subprocess` en `rutas/procesos.py` y `api/visor_perfiles.py` | Los comandos son listas fijas, sin `shell` y sin texto del usuario.                                 |
| `B311`         | `random` en `rutas/generador.py`                              | Genera grafos y consultas reproducibles con semilla; no es criptografía.                            |
| Vulture        | Campos de `NamedTuple` y rutas de FastAPI                     | Se leen por `_asdict` o por decorador; configurado en `pyproject.toml` y `vulture_lista_blanca.py`. |

### Medidas correctivas

- `B314` (análisis de XML no seguro): se reemplazó `xml.etree` por `defusedxml`.
- Dependencia vulnerable: se sube la versión mínima en `requirements.txt` y se vuelve a correr `pip-audit`.

## Configuración de Ruff

Su configuración está en `pyproject.toml` y activa:

- `E`, `W`: estilo (pycodestyle).
- `F`: errores (imports sin usar, variables no definidas).
- `I`: orden de los imports.
- `B`: errores probables (flake8-bugbear).
- `UP`, `C4`, `SIM`: sintaxis moderna y simplificaciones.
- `C90`: complejidad ciclomática máxima de 10 por función.
- `ERA`: código comentado.

## Uso local

```bash
ruff check .                 # análisis estático
ruff format .                # da formato al código
mypy                         # tipos
vulture                      # código muerto
bandit -r rutas api main.py -ll
pip-audit -r requirements.txt
pytest --cov --cov-report=xml
```

## API de la ventana

El módulo `api.calidad_router` consulta SonarQube Cloud. Su referencia (funciones, parámetros y variables de entorno) está en la <a href="../interna/referencia.html#api-modulos-api">Referencia del código</a>.
