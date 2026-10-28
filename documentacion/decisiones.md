# Decisiones de diseño y optimización

Este documento explica **qué** se decidió y **por qué**, para que quien modifique el código no deshaga una optimización sin volver a medir. La regla general es: primero una versión clara y correcta, después `cProfile` para ubicar el costo real, la mejora y una nueva medición (ver [Optimización y refactorización](optimizacion.md)). Las complejidades de cada algoritmo están en [Algoritmos y estructuras de datos](algoritmos.md) y los resultados medidos en [Rendimiento](rendimiento.md).

## Cola de prioridad en Dijkstra

`rutas/algoritmos/comunes.py` usa `heapq` para obtener siempre el nodo de menor costo. Esto da O((V+E) log V), frente a O(V²) de buscar el mínimo recorriendo todos los nodos, y es lo que permite llegar a 100.000 nodos. Las entradas obsoletas del heap se descartan al extraerlas en lugar de actualizarlas, porque `heapq` no permite modificar una prioridad.

*Cómo se verifica:* `tests/test_algoritmos.py` (resultados correctos) y el Performance Gate (tiempo).

## Conjunto en lugar de lista para los nodos cerrados

`cerrados` es un `set`: preguntar `actual in cerrados` es O(1). Con una lista sería O(n) por pregunta y el algoritmo se vuelve cuadrático. Está comprobado: `regresion_rendimiento.patch` hace ese cambio y la mediana de Dijkstra pasa de 12,6 ms a 306 ms con 20.000 nodos, unas 24 veces más lenta, sin que ninguna prueba funcional falle (el resultado es el mismo, solo cambia el tiempo).

*Cómo se verifica:* el Performance Gate falla con ese cambio. Es el motivo por el que existe: las pruebas de corrección no detectan una regresión de rendimiento.

## Un único bucle para Dijkstra y A\*

Pylint (`duplicate-code`) detectó el mismo bucle en ambos algoritmos. Ahora existe `buscar_con_heap()` y A\* solo le pasa su heurística. Se midió que Dijkstra queda dentro del ruido (±3 %) de la versión duplicada, así que no se pagó rendimiento por eliminar la repetición, y un cambio futuro se hace en un solo lugar.

## BFS con un solo diccionario

BFS usa `collections.deque` (cola con O(1) en ambos extremos; una lista sería O(n) al sacar el primer elemento) y un único diccionario de predecesores: que un nodo sea clave ya significa que fue descubierto, así que no hace falta un segundo conjunto de visitados.

## Heurística admisible en A\*

La heurística es la distancia euclídea **escalada** para que nunca sobrestime el costo real; si lo hiciera, A\* podría devolver una ruta que no es la más corta. El factor de escala se calcula una vez por versión del grafo y no en cada consulta.

## Representación del grafo

Listas de adyacencia en un `dict` (`{nodo: {vecino: peso}}`): acceso O(1) a un nodo o una conexión y espacio O(V+E), adecuado para grafos poco densos. Una matriz de adyacencia ocuparía O(V²), inviable con 100.000 nodos. Bloquear una conexión no la borra: los algoritmos la ignoran y se conserva su peso para poder habilitarla de nuevo.

## Caché acotada

`CacheRutas` guarda el resultado por `(origen, destino)`, se vacía cuando cambia `Grafo.version` y conserva como máximo 2.048 entradas, descartando la más antigua. Sin la invalidación devolvería rutas viejas tras editar el grafo; sin el tope, la memoria crecería sin límite.

## Sin paralelizar una sola búsqueda

Los hilos comparten el GIL y no aceleran trabajo de CPU puro; los procesos sí pueden, pero pagan crear el pool y copiar el grafo. Por eso solo se paralelizan lotes de 10 consultas y se compara secuencial, hilos y procesos en vez de suponer cuál conviene.

## Entrada/salida de archivos grandes

Se escribe con buffer (`writelines`) y se lee por lotes con `itertools.islice`, de modo que la memoria queda constante sin importar el tamaño del archivo. `mapear_acotado` limita los lotes en vuelo porque `Executor.map` consumiría el archivo entero de una vez.

## Medir tiempo y memoria por separado

`rutas/mediciones.py` mide el tiempo en una corrida limpia y la memoria en otra con `tracemalloc`, porque `tracemalloc` enlentece la ejecución y falsearía el tiempo. Por la misma razón `cerrojo_medicion` serializa las mediciones del servidor.

## Lógica sin web

`rutas` no importa `api` (ver [Arquitectura](arquitectura.md)). Así los algoritmos se prueban sin levantar un servidor y el pipeline puede ejecutar los gates de rendimiento y de memoria directamente desde la consola.

## Herramientas externas sin `shell`

`rutas/procesos.py` ejecuta `pytest`, `ruff` y las demás herramientas como `python -m modulo` con una lista de argumentos fija y un tiempo máximo. Evita la inyección de comandos y usa el mismo intérprete que la aplicación, así encuentra las herramientas de su entorno.

## Umbrales de los controles

| Control          | Umbral | Justificación                                                                                                                                                                                   |
|------------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Performance Gate | 500 ms | Dijkstra tarda unos 180 ms con 100.000 nodos: el margen absorbe la variación entre máquinas, y la regresión de la lista es mucho más lenta (con 100.000 nodos una sola consulta tarda minutos). |
| Memory Gate      | 32 MiB | El pico medido es de 15,2 MiB y no cambia entre corridas; el límite es el doble para tolerar diferencias entre versiones de Python.                                                             |
| Cobertura        | 90 %   | La cobertura real supera el 99 %; el umbral deja margen para código nuevo sin permitir que se abandonen las pruebas.                                                                            |
| Complejidad      | 10     | Una función de rango C o peor suele ser difícil de probar y de leer.                                                                                                                            |
