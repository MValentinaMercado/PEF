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

## Costo y utilidad: ¿cuándo conviene la IA?

La consigna pide justificar cuándo la IA aporta y cuándo una solución convencional es más simple, rápida, barata o confiable. La alternativa convencional a este modelo es **ejecutar el algoritmo y medir**. La sección «Costo y utilidad del modelo de IA» de la ventana Análisis tiene cuatro botones independientes (`rutas/evaluacion_modelo.py`):

| Medición | Qué responde | Endpoint |
|---|---|---|
| Costo de entrenar | Cuánto cuesta construir el modelo: medir los datos, ajustar (`fit`), memoria pico y tamaño | `POST /api/analisis/modelo/entrenamiento` |
| Precisión | MAE (ms) y error porcentual en grafos nuevos, contra predecir siempre el tiempo medio | `POST /api/analisis/modelo/precision` |
| Latencia y memoria | Cuánto tarda y cuánta memoria usa una predicción | `POST /api/analisis/modelo/latencia` |
| Predecir o ejecutar | Dijkstra real contra su predicción en grafos nuevos y estimaciones necesarias para amortizar el entrenamiento | `POST /api/analisis/modelo/comparacion` |

Los tiempos son la **mediana** de varias repeticiones (el ajuste, 5; la predicción, 5 bloques de 400 llamadas) y la memoria se mide en otra corrida con `tracemalloc`, porque una sola medición varía con la carga de la máquina.

### Conclusiones sin IA

Cada medición termina con una conclusión que redacta el código con reglas fijas y umbrales explícitos: el mismo resultado produce siempre el mismo texto. Los umbrales los define el equipo y están como constantes `UMBRAL_*` en `rutas/evaluacion_modelo.py`:

| Criterio | Umbral | Efecto en la conclusión |
|---|---|---|
| Error medio | hasta 10 % | «La precisión es buena para estimar tiempos» |
| Error medio | de 10 % a 25 % | «Aceptable para el orden de magnitud, no para diferencias pequeñas» |
| Error medio | más de 25 % | «Insuficiente: conviene medir directamente» |
| Latencia de una recomendación | menos de 1 ms | «Costo por consulta despreciable» |
| Estimaciones para amortizar el entrenamiento | más de 1.000 | «Conviene la solución convencional» |

### Ejemplo de resultado

Valores de una corrida de verificación (cambian con la máquina; los reales se ven en la ventana):

- **Entrenar** costó unos 3 s, de los cuales el ajuste de scikit-learn fue de aproximadamente 1 ms con unos 15 KB de pico. El modelo pesa menos de 1 KB. Casi todo el costo es **medir los grafos de ejemplo**, no aprender.
- **Precisión**: error absoluto medio de 2 ms y error porcentual medio de 10 % (A*) a 22 % (BFS y Dijkstra) en grafos que el modelo no vio, contra más del 50 % de la referencia sin IA.
- **Latencia**: unos 36 µs por predicción y 77 µs por recomendación, con 2,4 KB de pico.
- **Predecir o ejecutar**: de 100 a 40.000 nodos, Dijkstra tardó de 0,07 a 60 ms; predecirlo tarda unos 40 µs. En un grafo de 15.000 nodos la predicción erró casi 60 % (22 ms predichos contra 55 ms reales), así que el error depende del tamaño. El entrenamiento se recupera tras unas 50 estimaciones de grafos grandes.

### Cuándo conviene y cuándo no

- **La IA aporta** cuando hacen falta muchas estimaciones de grafos grandes (más de las necesarias para amortizar el entrenamiento) y se tolera un error de algunas decenas por ciento.
- **La solución convencional gana** si hay una sola consulta o un grafo chico (ejecutar tarda microsegundos o pocos milisegundos y es exacto, sin entrenar nada), si el error supera el umbral aceptable, si el grafo cae fuera del rango entrenado (el modelo extrapola mal) o si la máquina cambió (hay que volver a entrenar).
- **Elegir el algoritmo no mejora la regla fija** «siempre Dijkstra» (ver arriba): el aporte del modelo es predecir el tiempo, no decidir.

## Pruebas

Las pruebas no dependen de ninguna API externa. Se verifica que el modelo recupere los exponentes de una relación conocida, que acierte fuera del rango entrenado cuando los datos no tienen ruido, que BFS solo se recomiende sin pesos y que el endpoint exija entrenar antes de consultar (`tests/test_prediccion.py`). Las conclusiones y las mediciones de costo se prueban con datos sintéticos exactos y sus umbrales (`tests/test_modelo_costo.py`).

## Uso

```bash
curl -X POST http://127.0.0.1:8000/api/analisis/prediccion
curl "http://127.0.0.1:8000/api/analisis/prediccion/recomendar?nodos=100000&aristas=300000"
```
