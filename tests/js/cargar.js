"use strict";
/*
 * Carga los scripts de web/js en un contexto aislado de Node, con un DOM
 * mínimo simulado, para probar su lógica sin navegador.
 */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const RAIZ_JS = path.resolve(__dirname, "..", "..", "web", "js");

/** Elemento simulado: guarda lo que el código le asigna y acepta cualquier método. */
function crearElemento() {
  const propios = { value: "", checked: false, textContent: "", innerHTML: "", className: "", hidden: false };
  return new Proxy(propios, {
    get(objeto, nombre) {
      if (nombre in objeto) return objeto[nombre];
      if (nombre === "classList") return { add() {}, remove() {}, toggle() {}, contains: () => false };
      if (nombre === "style" || nombre === "dataset") return {};
      if (nombre === "children" || nombre === "rows") return [];
      if (nombre === "querySelectorAll") return () => [];
      if (nombre === "querySelector") return () => crearElemento();
      return () => crearElemento();
    },
    set(objeto, nombre, valor) {
      objeto[nombre] = valor;
      return true;
    },
  });
}

/** sessionStorage simulado; `fallar` hace que toda operación lance, como un navegador que lo bloquea. */
function crearAlmacen(inicial = {}) {
  const datos = new Map(Object.entries(inicial));
  const almacen = {
    fallar: false,
    getItem(clave) {
      if (almacen.fallar) throw new Error("almacenamiento bloqueado");
      return datos.has(clave) ? datos.get(clave) : null;
    },
    setItem(clave, valor) {
      if (almacen.fallar) throw new Error("almacenamiento bloqueado");
      datos.set(clave, String(valor));
    },
    datos,
  };
  return almacen;
}

/**
 * Crea un contexto con los scripts indicados cargados en orden.
 * `respuestas` asocia "MÉTODO /ruta" con el JSON que devolverá fetch.
 */
function cargar(scripts, { almacen = crearAlmacen(), respuestas = {} } = {}) {
  const elementos = new Map();
  const llamadas = [];
  const documento = {
    getElementById(id) {
      if (!elementos.has(id)) elementos.set(id, crearElemento());
      return elementos.get(id);
    },
    querySelectorAll: () => [],
    querySelector: () => crearElemento(),
    createElement: () => crearElemento(),
    createElementNS: () => crearElemento(),
    addEventListener() {},
  };
  const fetchSimulado = async (url, opciones = {}) => {
    const clave = `${opciones.method || "GET"} ${String(url).split("?")[0]}`;
    llamadas.push(clave);
    const cuerpo = respuestas[clave];
    if (cuerpo === undefined) {
      return { ok: false, statusText: "sin respuesta simulada", json: async () => ({}) };
    }
    return { ok: true, statusText: "OK", json: async () => cuerpo };
  };
  const contexto = vm.createContext({
    document: documento,
    sessionStorage: almacen,
    fetch: fetchSimulado,
    location: { hostname: "127.0.0.1" },
    performance: { now: () => 0 },
    URLSearchParams,
    console,
    setTimeout,
  });
  for (const nombre of scripts) {
    const archivo = path.join(RAIZ_JS, nombre);
    vm.runInContext(fs.readFileSync(archivo, "utf8"), contexto, { filename: archivo });
  }
  return {
    /** Evalúa una expresión en el contexto (accede a `const` y `function` de nivel superior). */
    evaluar: (codigo) => vm.runInContext(codigo, contexto),
    elemento: (id) => documento.getElementById(id),
    almacen,
    llamadas,
  };
}

/** Entrada de sessionStorage con el formato de guardarResultado. */
const guardado = (datos, fecha = "2026-11-04T12:00:00.000Z") =>
  JSON.stringify({ datos, guardado: fecha });

module.exports = { cargar, crearAlmacen, guardado };
