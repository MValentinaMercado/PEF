"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { cargar, crearAlmacen, guardado } = require("./cargar.js");

const nuevo = (opciones) => cargar(["comun.js"], opciones);

test("casiIguales usa la tolerancia del 5 %", () => {
  const c = nuevo();
  assert.equal(c.evaluar("TOLERANCIA_IGUALES"), 0.05);
  assert.equal(c.evaluar("casiIguales(100, 105)"), true);
  assert.equal(c.evaluar("casiIguales(100, 106)"), false);
  assert.equal(c.evaluar("casiIguales(105, 100)"), true, "es simétrica");
  assert.equal(c.evaluar("casiIguales(0, 0)"), true);
  assert.equal(c.evaluar("casiIguales(0, 1)"), false);
  assert.equal(c.evaluar("casiIguales(100, 150, 0.5)"), true, "acepta otra tolerancia");
});

test("listar une nombres en español", () => {
  const c = nuevo();
  assert.equal(c.evaluar("listar([])"), "");
  assert.equal(c.evaluar("listar(['A'])"), "A");
  assert.equal(c.evaluar("listar(['A', 'B'])"), "A y B");
  assert.equal(c.evaluar("listar(['A', 'B', 'C'])"), "A, B y C");
});

test("conMenor incluye valores casi iguales salvo que se pida lo exacto", () => {
  const c = nuevo();
  const filas = "[{n:'a',v:100},{n:'b',v:103},{n:'c',v:200}]";
  const nombres = (extra) => JSON.parse(c.evaluar(`JSON.stringify(conMenor(${filas}, (f) => f.v${extra}).filas.map((f) => f.n))`));
  assert.deepEqual(nombres(""), ["a", "b"]);
  assert.deepEqual(nombres(", false"), ["a"]);
});

test("compararMagnitud no presupone un ganador cuando los valores son similares", () => {
  const c = nuevo();
  const texto = c.evaluar(
    "compararMagnitud([{algoritmo:'BFS',v:100},{algoritmo:'Dijkstra',v:101}], (f) => f.v, 'Tiempo', (n) => n + ' ms')",
  );
  assert.equal(texto, "Tiempo: similar en todos (101 ms como máximo).");
});

test("compararMagnitud concuerda el verbo con la cantidad de algoritmos", () => {
  const c = nuevo();
  const uno = c.evaluar(
    "compararMagnitud([{algoritmo:'BFS',v:10},{algoritmo:'Dijkstra',v:50}], (f) => f.v, 'Tiempo', (n) => n + ' ms')",
  );
  assert.equal(uno, "Tiempo: BFS registra menos (10 ms frente a 50 ms).");
  const varios = c.evaluar(
    "compararMagnitud([{algoritmo:'BFS',v:10},{algoritmo:'A*',v:10},{algoritmo:'Dijkstra',v:50}], (f) => f.v, 'Tiempo', (n) => n + ' ms')",
  );
  assert.equal(varios, "Tiempo: BFS y A* registran menos (10 ms frente a 50 ms).");
});

test("guardarResultado y leerResultado conservan los datos y la fecha", () => {
  const c = nuevo();
  c.evaluar("guardarResultado('prueba', { a: 1 })");
  const leido = c.evaluar("leerResultado('prueba')");
  assert.deepEqual(JSON.parse(JSON.stringify(leido.datos)), { a: 1 });
  assert.ok(!Number.isNaN(Date.parse(leido.guardado)));
  assert.ok(c.almacen.datos.has("resultado:prueba"));
});

test("guardar null descarta el resultado guardado", () => {
  const c = nuevo({ almacen: crearAlmacen({ "resultado:x": guardado({ a: 1 }) }) });
  c.evaluar("guardarResultado('x', null)");
  assert.equal(c.evaluar("leerResultado('x').datos"), null);
});

test("leerResultado devuelve null si no hay datos o el contenido es inválido", () => {
  const c = nuevo({ almacen: crearAlmacen({ "resultado:roto": "{no es json" }) });
  assert.equal(c.evaluar("leerResultado('inexistente')"), null);
  assert.equal(c.evaluar("leerResultado('roto')"), null);
});

test("si el navegador bloquea el almacenamiento no se lanza ninguna excepción", () => {
  const almacen = crearAlmacen();
  almacen.fallar = true;
  const c = nuevo({ almacen });
  assert.doesNotThrow(() => c.evaluar("guardarResultado('x', { a: 1 })"));
  assert.equal(c.evaluar("leerResultado('x')"), null);
});

test("etiquetaResultadoGuardado indica que el resultado es de la pestaña", () => {
  const c = nuevo();
  assert.equal(c.evaluar("etiquetaResultadoGuardado(null)"), "");
  assert.equal(
    c.evaluar("etiquetaResultadoGuardado({ guardado: 'fecha inválida' })"),
    "Resultado guardado en esta pestaña.",
  );
  assert.match(
    c.evaluar("etiquetaResultadoGuardado({ guardado: '2026-11-04T12:00:00.000Z' })"),
    /^Último resultado de esta pestaña: .+\.$/,
  );
});
