"""Falsos positivos de Vulture (cada grupo está justificado).

Vulture solo ve nombres escritos en el código. Los campos de las
``NamedTuple`` se leen al convertir la fila a JSON (``_asdict``) y desde el
navegador, así que parecen sin uso pero son datos de la respuesta de la API.
"""

from vulture.whitelist_utils import Whitelist

campos_de_filas = Whitelist()

# rutas/concurrencia.py: FilaConcurrencia
campos_de_filas.modo
campos_de_filas.consultas_procesadas
campos_de_filas.aceleracion

# rutas/entrada_salida.py: filas de comparación de lectura y escritura
campos_de_filas.tamano_lote_paralelo
campos_de_filas.resultados_coinciden

# rutas/informacion.py: ficha descriptiva de cada algoritmo
campos_de_filas.funcionamiento
campos_de_filas.complejidad_temporal
campos_de_filas.complejidad_espacial
campos_de_filas.estructuras
campos_de_filas.uso_estructuras

# rutas/perfilado.py: filas de tiempo y de memoria
campos_de_filas.tiempo_acumulado
campos_de_filas.memoria_mib
campos_de_filas.incremento_mib

# rutas/perfilado.py y rutas/perfilado_scalene.py: filas de line_profiler y
# de Scalene
campos_de_filas.tiempo_us
campos_de_filas.porcentaje
campos_de_filas.segundos
campos_de_filas.fraccion_python

# rutas/escalabilidad.py: filas del benchmark y memoria de cada grafo
campos_de_filas.us_por_nodo
campos_de_filas.esperado_ms
campos_de_filas.razon
campos_de_filas.esperado_explorados_ms
campos_de_filas.razon_explorados
campos_de_filas.memoria_mb

# rutas/prediccion.py: resultados de la regresión de tiempos
campos_de_filas.medido_ms
campos_de_filas.predicho_ms
campos_de_filas.error_pct
campos_de_filas.r2_entrenamiento
campos_de_filas.error_medio_pct
campos_de_filas.exponente_nodos
campos_de_filas.exponente_aristas
campos_de_filas.aciertos_regla_fija
campos_de_filas.regla_fija
campos_de_filas.predicciones_ms
