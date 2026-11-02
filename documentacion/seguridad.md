# Seguridad

Esta página resume los riesgos de la aplicación y cómo se controlan. La política de bloqueo del pipeline, las excepciones justificadas y las medidas correctivas están en [Análisis de calidad](calidad.md).

## Riesgos identificados

| Riesgo                                                         | Medida                                                                                                                  | Control                                                    |
|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| La API no tiene autenticación.                                 | El servidor escucha solo en `127.0.0.1`. No debe exponerse a una red sin un proxy que autentique.                       | `main.py` (`host="127.0.0.1"`)                             |
| Entradas inválidas o maliciosas (nombres, coordenadas, pesos). | Cada entrada se valida con modelos pydantic (rangos, formato del nombre) y la lógica rechaza duplicados e inexistentes. | `api/esquemas.py`, `tests/test_api.py`                     |
| Ejecución de herramientas externas.                            | Se ejecutan como `python -m modulo` con argumentos fijos, sin `shell` y con tiempo máximo.                              | `rutas/procesos.py`; Bandit (reglas B404 y B603 aceptadas) |
| Lectura de XML de resultados de pruebas.                       | Se usa `defusedxml` en lugar de `xml.etree`.                                                                            | `api/pruebas_router.py`; Bandit                            |
| Secretos (token de SonarQube Cloud).                           | No está en el repositorio: es el secret `SONAR_TOKEN` de GitHub o una variable de entorno.                              | Gitleaks en cada corrida                                   |
| Dependencias con vulnerabilidades conocidas.                   | Se auditan en cada corrida y Dependabot propone actualizaciones semanales.                                              | pip-audit, Dependabot                                      |
| Estado compartido entre peticiones.                            | Un cerrojo protege el grafo y otro serializa las mediciones.                                                            | `api/estado.py`                                            |
| Cambios que rompen los controles.                              | La rama `main` debe exigir el check **Resultado final** antes de aceptar un Pull Request.                               | Protección de rama (ver [Mantenimiento](mantenimiento.md))                   |

## Dependencias vulnerables

`pip-audit` revisa `requirements.txt` en cada corrida y deja el informe `pip-audit.json` como artefacto. Cuando informe una vulnerabilidad se registra aquí junto con su medida:

| Paquete              | Identificador | Estado | Medida correctiva                                                              |
|----------------------|---------------|--------|--------------------------------------------------------------------------------|
| (ninguno registrado) |               |        | Subir la versión mínima en `requirements.txt` y volver a ejecutar `pip-audit`. |

## Procedimiento ante un hallazgo

1.  Reproducirlo en local (`bandit -r rutas api main.py -ll` o `pip-audit -r requirements.txt`).
2.  Si es real, corregirlo y confirmar que el control vuelve a aprobar.
3.  Si es un falso positivo, no desactivar la regla en general: documentar la excepción en [Análisis de calidad](calidad.md) con el motivo.
4.  Si es un secreto, **revocarlo** y generar uno nuevo: borrarlo del código no alcanza porque queda en el historial de Git.
