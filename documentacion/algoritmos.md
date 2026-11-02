# Algoritmos y estructuras de datos

El grafo es **no dirigido y ponderado** y se representa con listas de adyacencia guardadas en un `dict`: `{nodo: {vecino: peso}}`. Así el acceso a un nodo o a una conexión es O(1) y el espacio total es O(V+E). Cada nodo tiene una posición `(x, y)`, y una conexión puede marcarse como bloqueada: los algoritmos la ignoran sin que se pierda su peso.

Todos los algoritmos comparten la misma firma `(grafo, origen, destino)` y devuelven un `rutas.algoritmos.comunes.ResultadoBusqueda` con la ruta, la distancia y la cantidad de nodos explorados. El registro `ALGORITMOS` asocia cada nombre con su función; el editor, la caché, el benchmark y el perfilado lo recorren, por lo que agregar un algoritmo no exige modificar esos módulos.

| Algoritmo | Funcionamiento                                                                                                                                  | Complejidad temporal                 | Complejidad espacial |
|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|----------------------|
| BFS       | Menor cantidad de aristas (cola FIFO, `collections.deque`). Un único diccionario de predecesores indica a la vez qué nodos fueron descubiertos. | O(V+E)                               | O(V)                 |
| Dijkstra  | Menor costo con pesos no negativos (cola de prioridad, `heapq`). Las entradas obsoletas del heap se descartan al extraerlas.                    | O((V+E) log V) con heap binario      | O(V)                 |
| A\*       | Dijkstra guiado por una heurística euclídea escalada para que sea admisible. El factor de escala se calcula una vez por versión del grafo.      | Depende de la heurística y del grafo | O(V) en el peor caso |

*V* es la cantidad de nodos y *E* la de aristas. Las complejidades corresponden a implementaciones habituales, no a cualquier implementación posible.

## Caché

`rutas.cache.CacheRutas` memoriza el resultado por `(origen, destino)`. El algoritmo se elige al crearla (Dijkstra por defecto). Se vacía sola cuando cambia `Grafo.version` y conserva como máximo 2.048 entradas, descartando la más antigua cuando se llena. Los contadores `aciertos`, `fallos` e `invalidaciones` permiten medir su efecto.

## Concurrencia

Los hilos comparten el GIL, por lo que en tareas de CPU puro no aceleran; los procesos sí pueden, pero pagan el costo de crear el pool y copiar el grafo (ver `rutas.concurrencia`). Las consultas se reparten en lotes de 10.

## Entrada/salida con archivos grandes

Una operación de E/S es mucho más lenta que una operación en memoria, así que conviene reducir su cantidad y no cargar el archivo entero (ver `rutas.entrada_salida`):

- **Buffer** al escribir: se acumulan las líneas y se escriben juntas con `writelines`, en vez de una operación por línea.
- **Batching** al leer: `leer_en_lotes` recorre el archivo en grupos de `N` líneas con `itertools.islice`; la memoria se mantiene constante.
- **Procesamiento en paralelo**: cada lote se envía a un hilo o a un proceso y los resultados parciales se combinan. `mapear_acotado` limita cuántos lotes hay en vuelo, porque `Executor.map` consumiría todo el archivo de una vez.

## Mediciones

`rutas.mediciones` mide el tiempo y el pico de memoria de cada consulta. Se hacen en dos corridas separadas porque `tracemalloc` enlentece la ejecución y falsearía el tiempo. La memoria informada pertenece a la operación medida, no al proceso completo.
