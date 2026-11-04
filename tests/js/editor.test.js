"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { cargar, crearAlmacen, guardado } = require("./cargar.js");

const GRAFO = {
  nodos: [{ nombre: "A", x: 0, y: 0 }, { nombre: "B", x: 1, y: 1 }],
  aristas: [{ a: "A", b: "B", peso: 3, bloqueada: false }],
};
const RESULTADOS = [
  { algoritmo: "BFS", ruta: ["A", "B"], distancia: 3, tiempo_ms: 0.1, memoria_kb: 1, nodos_explorados: 2 },
];
const guardadoEditor = (grafo, origen = "A", destino = "B") =>
  guardado({ origen, destino, grafo, resultados: RESULTADOS });

/** Carga el Editor con el grafo del servidor y espera a que termine su inicio. */
async function abrirEditor(almacenado, grafoServidor = GRAFO) {
  const almacen = crearAlmacen(almacenado === null ? {} : { "resultado:editor": almacenado });
  const c = cargar(["comun.js", "editor.js"], { almacen, respuestas: { "GET /api/grafo": grafoServidor } });
  await new Promise((resolver) => setTimeout(resolver, 10));
  return c;
}

test("el Editor restaura la última comparación si el grafo no cambió", async () => {
  const c = await abrirEditor(guardadoEditor(GRAFO));
  assert.equal(c.evaluar("resultados.length"), 1);
  assert.equal(c.evaluar("resultados[0].algoritmo"), "BFS");
  assert.match(c.elemento("estado-resultados").textContent, /^Último resultado de esta pestaña:/);
});

test("el Editor descarta la comparación guardada si el grafo cambió", async () => {
  const otro = { ...GRAFO, aristas: [{ a: "A", b: "B", peso: 9, bloqueada: false }] };
  const c = await abrirEditor(guardadoEditor(GRAFO), otro);
  assert.equal(c.evaluar("resultados.length"), 0);
  assert.equal(c.evaluar("leerResultado('editor').datos"), null);
});

test("el Editor descarta la comparación si el origen o el destino ya no existen", async () => {
  const c = await abrirEditor(guardadoEditor(GRAFO, "A", "Z"));
  assert.equal(c.evaluar("resultados.length"), 0);
  assert.equal(c.evaluar("leerResultado('editor').datos"), null);
});

test("sin resultado guardado el Editor arranca vacío y sin errores", async () => {
  const c = await abrirEditor(null);
  assert.equal(c.evaluar("resultados.length"), 0);
});
