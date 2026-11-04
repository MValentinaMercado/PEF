# IA aplicada al desarrollo

El proyecto tiene dos enfoques de IA. Esta página documenta el primero: usar asistentes de programación para generar pruebas, explicar código, detectar errores y proponer optimizaciones, **validando siempre sus resultados**. El segundo enfoque, la IA dentro de la aplicación, está en [Componente de IA](ia.md).

## Regla de trabajo

Una propuesta de un asistente no se acepta por venir de una IA. Se acepta si, después de aplicarla, siguen pasando los mismos controles que exige el pipeline de CI: Ruff, mypy, Vulture, Pylint, Radon, Bandit, `pytest` con cobertura mínima del 80 % y los gates de rendimiento y memoria. Una mejora de rendimiento solo se considera tal si una medición la respalda.

## Registro de uso

| Fecha | Asistente | Tarea | Propuesta | Decisión | Cómo se validó |
|---|---|---|---|---|---|
| 29/10/2026 | Claude (Anthropic) | Revisar el estado del proyecto contra la consigna | Correr todos los controles del CI en local y compararlos con la matriz de la consigna | Aceptada | Se detectó un `E501` de Ruff y que `pytest --cov` fallaba en local (doctest de `memory_profiler`) |
| 29/10/2026 | Claude | Corregir el fallo local de cobertura | Fijar `core = "sysmon"` en `pyproject.toml` | Aceptada | `pytest --cov` pasa sin la variable `COVERAGE_CORE`, igual que en el CI |
| 29/10/2026 | Claude | Detectar código muerto | Vulture al 30 % de confianza, más búsqueda de funciones, clases CSS e identificadores sin uso en `web/` | Aceptada en parte | En Python no había código muerto (solo los campos de `NamedTuple` ya justificados en `vulture_lista_blanca.py`) |
| 29/10/2026 | Claude | Eliminar código muerto de la web | Quitar la constante `GRAFICOS`, dos variables sin lectura y un `id` huérfano | Aceptada | `node --check` de cada archivo JS y pruebas de la interfaz |
| 29/10/2026 | Claude | Eliminar identificadores «sin uso» de las páginas | Quitar `res-*`, `criterio-*`, `tabla-*` de `optimizacion.html` y los `id` de los iframes | **Rechazada** | Falso positivo: se arman en JavaScript con plantillas (`res-${nombre}`) y desde un script de la página |
| 29/10/2026 | Claude | Duplicación en JavaScript | `ficha()` repetida en tres archivos y `const el` en seis: dejar una sola copia en `comun.js` | Aceptada | Las copias eran equivalentes (se revisó cada uso) y todos los scripts cargan `comun.js` primero |
| 29/10/2026 | Claude | Medir el costo del modelo de scikit-learn | Módulo `rutas/evaluacion_modelo.py`, cuatro endpoints y una sección en Análisis | Aceptada con cambios | Radon marcó dos funciones de complejidad C (12 y 11): se dividieron antes de aceptar el código |
| 29/10/2026 | Claude | Generar pruebas | `tests/test_modelo_costo.py` y `tests/test_ci_github.py` | Aceptada | Cobertura de los módulos nuevos: 100 %. Dos doctests escritos por el asistente fallaron al principio (un texto esperado distinto del real y un redondeo) y se corrigieron |
| 29/10/2026 | Claude | Mostrar el estado del CI en la ventana Calidad | Módulo `api/ci_github.py` y sección en `/calidad`, con el token solo en el servidor | Aceptada | Pruebas con la API de GitHub simulada; solo se entregan enlaces `https` |

## Qué revisó una persona

Los umbrales de las conclusiones automáticas (10 %, 25 %, 1 ms y 1.000 estimaciones, y el 5 % con que la interfaz considera «casi iguales» dos valores) fueron una propuesta del asistente. Son criterios de diseño y los define el equipo: están como constantes en `rutas/evaluacion_modelo.py`.

## Otros usos del asistente (completar)

Cada integrante agrega aquí lo que hizo con su asistente (GitHub Copilot u otro), con el mismo formato:

| Fecha | Asistente | Tarea | Propuesta | Decisión (aceptada, modificada o rechazada) | Cómo se validó |
|---|---|---|---|---|---|
| | | | | | |

## Limitaciones conocidas

- Un asistente puede proponer cambios incorrectos con total seguridad: por eso ninguna propuesta se acepta sin controles automáticos.
- Un código generado por IA no es mejor por defecto. El caso de Radon (arriba) muestra que cumplió la función pedida y aun así incumplía el límite de complejidad del proyecto.
- Las conclusiones de la aplicación no las redacta una IA: salen de reglas fijas sobre números medidos, para que sean reproducibles.
