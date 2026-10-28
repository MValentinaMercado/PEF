# Componente de IA: predicción de rendimiento

## Qué problema resuelve

Medir cuánto tarda cada algoritmo en un grafo grande lleva tiempo (el benchmark de 100.000 nodos tarda unos 20 segundos). El modelo aprende de mediciones reales y permite **anticipar** el tiempo de un grafo que todavía no se midió. Es una tarea de **regresión** (predecir un número), la que la clase propone en "Usar IA para detectar cuellos de botella".

## Cómo funciona

- **Datos**: se miden en el momento, sin servicios externos. Para cada uno de 40 grafos de entrenamiento (de 500 a 10.000 nodos y de 2 a 8 aristas por nodo) se mide el tiempo medio por consulta de BFS, Dijkstra y A\* (`rutas.prediccion.medir_muestras`).
- **Modelo**: `LinearRegression` de scikit-learn, uno por algoritmo, sobre logaritmos: `ln(t) = a + b·ln(V) + c·ln(E)`. Es equivalente a `t = e^a · V^b · E^c`. Se usan logaritmos porque el tiempo no crece en línea recta con el tamaño, y así los exponentes `b` y `c` se pueden comparar con la complejidad teórica de la ventana Análisis.
- **Evaluación**: con 5 grafos que el modelo no vio, algunos más grandes que todo el entrenamiento. Se informa el error medio y el R² (sobre el logaritmo del tiempo).
- **Recomendación**: entre los algoritmos *correctos* para el problema se elige el de menor tiempo predicho. BFS minimiza saltos y no costo, así que solo es candidato si el grafo no tiene pesos.

## Por qué regresión lineal y no otro modelo

Con pocas variables (dos) y pocos datos (60 muestras) un modelo simple es suficiente, se entrena en milisegundos, no depende de servicios externos y es interpretable: los exponentes dicen cómo escala cada algoritmo. Un modelo más complejo se ajustaría al ruido de las mediciones.

## Resultados y límites

- En grafos nuevos el error medio es del orden del 10 % y varía entre corridas porque las mediciones dependen de la máquina y de la carga.
- **Elegir el algoritmo no mejora la regla fija.** El modelo y la regla "siempre Dijkstra" aciertan lo mismo, porque en estos grafos Dijkstra es siempre más rápido que A\* (la heurística es débil y A\* explora casi los mismos nodos). El aporte del modelo es predecir el tiempo, no elegir. La ventana Análisis muestra ambos resultados lado a lado.
- **Extrapola mal**: ajustado a grafos de hasta 10.000 nodos, subestima los tiempos de 100.000 nodos, donde cada nodo cuesta más (caché de CPU, memoria). Por eso la aplicación advierte cuando la consulta cae fuera del rango visto (`rutas.prediccion.advertencias`).
- **Depende de la máquina**: se entrena con mediciones de este equipo y hay que volver a entrenarlo en otro.

## Pruebas

Las pruebas no dependen de ninguna API externa. Se verifica que el modelo recupere los exponentes de una relación conocida, que acierte fuera del rango entrenado cuando los datos no tienen ruido, que BFS solo se recomiende sin pesos y que el endpoint exija entrenar antes de consultar (`tests/test_prediccion.py`).

## Uso

```bash
curl -X POST http://127.0.0.1:8000/api/analisis/prediccion
curl "http://127.0.0.1:8000/api/analisis/prediccion/recomendar?nodos=100000&aristas=300000"
```
