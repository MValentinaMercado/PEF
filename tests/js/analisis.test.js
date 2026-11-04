"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { cargar, crearAlmacen, guardado } = require("./cargar.js");

const nuevo = (opciones) => cargar(["comun.js", "analisis.js"], opciones);
const esperar = () => new Promise((resolver) => setImmediate(resolver));

const CACHE = {
  total_consultas: 100,
  pares_distintos: 20,
  aciertos: 80,
  fallos: 20,
  sin_cache: [100, 50],
  con_cache: [20, 60],
  fallo_tras_cambio: true,
  acierto_al_repetir: true,
};

// ------------------------------------------------------------ interpretaciones
test("analizarCache usa los números reales y no presupone resultados", () => {
  const c = nuevo();
  c.evaluar(`globalThis.r = ${JSON.stringify(CACHE)}`);
  const texto = c.evaluar("analizarCache(r)");
  assert.match(texto, /80 de 100 consultas \(80,0 %\) salieron de la caché/);
  assert.match(texto, /es el máximo posible/);
  assert.match(texto, /5,0 veces menor/);

  const sinMejora = c.evaluar(
    "analizarCache({ ...r, con_cache: [101, 50], aciertos: 10, fallo_tras_cambio: false, acierto_al_repetir: false })",
  );
  assert.match(sinMejora, /no cambió el tiempo de forma apreciable/);
  assert.match(sinMejora, /el máximo posible con 20 pares distintos era 80/);
  assert.match(sinMejora, /conviene revisar la invalidación/);
  assert.match(sinMejora, /no produjo un acierto de caché/);
});

test("analizarConcurrencia describe valores casi iguales como prácticamente lo mismo", () => {
  const c = nuevo();
  const texto = c.evaluar(`analizarConcurrencia([
    { modo: "Secuencial", aceleracion: 1, memoria_kb: 10 },
    { modo: "Hilos (4)", aceleracion: 1.03, memoria_kb: 10 },
    { modo: "Procesos (4)", aceleracion: 2, memoria_kb: 10 },
  ])`);
  assert.match(
    texto,
    /Hilos \(4\) tardó prácticamente lo mismo que Secuencial/,
  );
  assert.match(texto, /Procesos \(4\) fue 2,00× más rápido que Secuencial/);
  assert.match(texto, /Los procesos aceleraron y los hilos no/);
});

test("lecturaParalelismo cubre los cuatro casos", () => {
  const c = nuevo();
  const caso = (h, p) =>
    c.evaluar(
      `lecturaParalelismo([{ modo: "Hilos", aceleracion: ${h} }, { modo: "Procesos", aceleracion: ${p} }])`,
    );
  assert.match(caso(1, 2), /^Los procesos aceleraron y los hilos no/);
  assert.match(caso(1, 0.5), /^Ni hilos ni procesos aceleraron/);
  assert.match(caso(2, 1), /^Los hilos aceleraron y los procesos no/);
  assert.match(caso(2, 3), /^Tanto hilos como procesos aceleraron/);
  assert.equal(
    c.evaluar('lecturaParalelismo([{ modo: "Hilos", aceleracion: 2 }])'),
    "",
  );
});

test("analizarGrupo distingue si menos nodos explorados se tradujo en menor tiempo", () => {
  const c = nuevo();
  const grupo = (tiempoA) => `analizarGrupo([
    { algoritmo: "Dijkstra", tiempo_ms: 10, nodos_explorados: 1000, memoria_kb: 5 },
    { algoritmo: "A*", tiempo_ms: ${tiempoA}, nodos_explorados: 500, memoria_kb: 5 },
  ])`;
  assert.match(c.evaluar(grupo(5)), /eso se tradujo en menor tiempo/);
  assert.match(c.evaluar(grupo(20)), /pero no tardó menos/);
  assert.match(
    c.evaluar(grupo(10.2)),
    /pero no tardó menos/,
    "una diferencia menor al 5 % no cuenta",
  );
  assert.equal(
    c.evaluar('analizarGrupo([{ algoritmo: "BFS" }])'),
    "Con un solo algoritmo no hay comparación posible.",
  );
});

test("BFS no entra en las comparaciones: se describe como costo base sin pesos", () => {
  const c = nuevo();
  const texto = c.evaluar(`analizarGrupo([
    { algoritmo: "BFS", tiempo_ms: 1, nodos_explorados: 100, memoria_kb: 1 },
    { algoritmo: "Dijkstra", tiempo_ms: 10, nodos_explorados: 1000, memoria_kb: 5 },
    { algoritmo: "A*", tiempo_ms: 10.2, nodos_explorados: 1000, memoria_kb: 5 },
  ])`);
  assert.match(
    texto,
    /^Tiempo: similar en todos/,
    "compara solo Dijkstra y A*",
  );
  assert.doesNotMatch(texto, /BFS registra/);
  assert.match(
    texto,
    /BFS sirve para conocer el costo base de recorrer el grafo sin manejar pesos: tardó 1,0000 ms/,
  );
});

test("analizarBenchmark compara solo Dijkstra y A* y trata a BFS como costo base", () => {
  const c = nuevo();
  const texto = c.evaluar(`analizarBenchmark([
    { algoritmo: "BFS", nodos: 100, tiempo_ms: 1 },
    { algoritmo: "Dijkstra", nodos: 100, tiempo_ms: 5 },
    { algoritmo: "A*", nodos: 100, tiempo_ms: 5.1 },
    { algoritmo: "BFS", nodos: 1000, tiempo_ms: 10 },
    { algoritmo: "Dijkstra", nodos: 1000, tiempo_ms: 60 },
    { algoritmo: "A*", nodos: 1000, tiempo_ms: 30 },
  ], [100, 1000])`);
  assert.match(
    texto,
    /Entre Dijkstra y A\*, 100 nodos: tiempos similares; 1\.000 nodos: menor tiempo en A\*/,
  );
  assert.match(texto, /El orden en tiempo cambia con el tamaño/);
  assert.match(
    texto,
    /BFS sirve para conocer el costo base de recorrer el grafo sin manejar pesos/,
  );
  assert.doesNotMatch(texto, /menor tiempo en BFS/);
  assert.equal(c.evaluar("analizarBenchmark([], [])"), "");
});

test("analizarEvaluaciones no incluye a BFS en el ajuste, el error ni los exponentes", () => {
  const c = nuevo();
  const texto = c.evaluar(`analizarEvaluaciones([
    { algoritmo: "BFS", r2_entrenamiento: 0.885, error_medio_pct: 28, exponente_nodos: 0.5, exponente_aristas: 0.37 },
    { algoritmo: "Dijkstra", r2_entrenamiento: 0.95, error_medio_pct: 16, exponente_nodos: 0.5, exponente_aristas: 0.42 },
    { algoritmo: "A*", r2_entrenamiento: 0.97, error_medio_pct: 17, exponente_nodos: 0.5, exponente_aristas: 0.44 },
  ])`);
  assert.match(
    texto,
    /Entre Dijkstra y A\*, el ajuste más flojo es el de Dijkstra \(R² 0,950\)/,
  );
  assert.match(
    texto,
    /Suma de exponentes b\+c.*: Dijkstra 0,92 \(menos que lineal\), A\* 0,94 \(menos que lineal\)\./,
  );
  assert.doesNotMatch(
    texto.split("BFS sirve")[0],
    /BFS/,
    "BFS solo aparece en su frase aparte",
  );
  assert.match(
    texto,
    /BFS sirve para conocer el costo base de recorrer el grafo sin manejar pesos: R² 0,885/,
  );
});

// ----------------------------------------------------------------- persistencia
test("al abrir la ventana se restauran los resultados guardados sin llamar a la API", async () => {
  const c = nuevo({
    almacen: crearAlmacen({ "resultado:analisis:cache": guardado(CACHE) }),
  });
  await esperar();
  assert.match(c.elemento("texto-cache").textContent, /80 de 100 consultas/);
  assert.match(
    c.elemento("estado-cache").textContent,
    /^Último resultado de esta pestaña:/,
  );
  assert.deepEqual(c.llamadas, []);
});

test("un resultado con formato inválido se descarta y no rompe la ventana", () => {
  const c = nuevo({
    almacen: crearAlmacen({
      "resultado:analisis:cache": guardado({ roto: true }),
    }),
  });
  assert.equal(c.evaluar("leerResultado('analisis:cache').datos"), null);
  assert.equal(c.elemento("texto-cache").textContent, "");
});

test("restaurar el perfilado no inicia SnakeViz", async () => {
  const perfil = { cpu: { BFS: [], Dijkstra: [], "A*": [] }, memoria: {} };
  const c = nuevo({
    almacen: crearAlmacen({ "resultado:analisis:perfilado": guardado(perfil) }),
  });
  await esperar();
  assert.ok(
    !c.llamadas.some((l) => l.includes("snakeviz")),
    c.llamadas.join(", "),
  );
  assert.equal(
    c.elemento("estado-snakeviz").textContent,
    "SnakeViz se inicia al ejecutar el perfilado.",
  );
});

test("ejecutar desde el botón consulta la API, muestra la conclusión y guarda el resultado", async () => {
  const c = nuevo({ respuestas: { "POST /api/analisis/cache": CACHE } });
  await c.evaluar("ejecutarCache()");
  assert.deepEqual(c.llamadas, ["POST /api/analisis/cache"]);
  assert.match(c.elemento("texto-cache").textContent, /80 de 100 consultas/);
  assert.match(c.elemento("estado-cache").textContent, /^Ejecutado ahora en /);
  assert.equal(c.evaluar("leerResultado('analisis:cache').datos.aciertos"), 80);
});

test("si la API falla se informa el error y se conserva el resultado guardado", async () => {
  const c = nuevo({
    almacen: crearAlmacen({ "resultado:analisis:cache": guardado(CACHE) }),
  });
  await c.evaluar("ejecutarCache()"); // fetch simulado sin respuesta: error
  assert.match(
    c.elemento("estado-cache").textContent,
    /última ejecución guardada/,
  );
  assert.equal(c.evaluar("leerResultado('analisis:cache').datos.aciertos"), 80);
});

test("la consulta del modelo se restaura con sus valores y su conclusión", () => {
  const recomendacion = {
    consulta: { nodos: "5000", aristas: "20000", ponderado: true },
    r: {
      algoritmo: "BFS",
      predicciones_ms: { BFS: 1, Dijkstra: 5 },
      advertencias: [],
    },
  };
  const c = nuevo({
    almacen: crearAlmacen({
      "resultado:analisis:recomendar": guardado(recomendacion),
    }),
  });
  assert.equal(c.elemento("ia-nodos").value, "5000");
  assert.equal(c.elemento("ia-aristas").value, "20000");
  assert.equal(c.elemento("ia-ponderado").checked, true);
  assert.equal(
    c.elemento("texto-recomendacion").textContent,
    "BFS es el de menor tiempo predicho.",
  );
  assert.match(
    c.elemento("estado-recomendar").textContent,
    /^Último resultado de esta pestaña:/,
  );
});

test("una consulta guardada con formato inválido se descarta", () => {
  const c = nuevo({
    almacen: crearAlmacen({
      "resultado:analisis:recomendar": guardado({ consulta: {}, r: {} }),
    }),
  });
  assert.equal(c.evaluar("leerResultado('analisis:recomendar').datos"), null);
});
