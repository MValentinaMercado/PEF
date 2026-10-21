/* Ventana 1: editor del grafo (SVG) y búsqueda de rutas. */
const NS = "http://www.w3.org/2000/svg";
const RADIO = 16;
const COLOR = {
  nodo: "#22364d",
  anillo: "#7fb2e5",
  texto: "#e8eef5",
  origen: "#4cc38a",
  destino: "#e8b04a",
  bloqueo: "#ef6f6c",
  arista: "#5d6b7c",
  etiqueta: "#161d26",
  seleccion: "#ffffff",
};

const el = (id) => document.getElementById(id);
const lienzo = el("lienzo");
let grafo = { nodos: [], aristas: [] };
let seleccion = null; // {tipo: "nodo", nombre} | {tipo: "arista", a, b}
let pendiente = null; // primer nodo de una conexión a medio crear
let resultados = []; // filas devueltas por /api/rutas
let rutaVisible = [];
let colorRuta = COLOR.origen;
let arrastre = null; // {nombre} mientras se mueve un nodo

const modo = () => document.querySelector("input[name=modo]:checked").value;
const posicion = (n) => grafo.nodos.find((x) => x.nombre === n);
const mismaArista = (e, a, b) =>
  (e.a === a && e.b === b) || (e.a === b && e.b === a);

function mensaje(texto, esError = false) {
  const p = el("mensaje");
  p.textContent = texto;
  p.className = "estado" + (esError ? " error" : "");
}

/** Pide un valor con un <dialog>; devuelve null si se cancela. */
function pedir(etiqueta, valor, tipo = "text") {
  const dialogo = el("dialogo");
  const campo = el("dialogo-campo");
  el("dialogo-etiqueta").firstChild.textContent = etiqueta + " ";
  campo.type = tipo;
  campo.value = valor;
  if (tipo === "number") {
    campo.step = "any";
    campo.min = "0.01";
  }
  return new Promise((resolver) => {
    dialogo.addEventListener(
      "close",
      () => resolver(dialogo.returnValue === "ok" ? campo.value : null),
      { once: true },
    );
    dialogo.showModal();
    campo.select();
  });
}

/** Aplica el estado nuevo devuelto por la API y redibuja. */
function aplicar(nuevo, limpiarResultados = true) {
  grafo = nuevo;
  if (limpiarResultados) {
    resultados = [];
    rutaVisible = [];
    mostrarResultados();
  }
  const nombres = grafo.nodos.map((n) => n.nombre);
  for (const id of ["origen", "destino"]) {
    const combo = el(id),
      previo = combo.value;
    combo.innerHTML = nombres.map((n) => `<option>${esc(n)}</option>`).join("");
    combo.value = nombres.includes(previo)
      ? previo
      : (id === "origen" ? nombres[0] : nombres[nombres.length - 1]) || "";
  }
  if (seleccion && !existe(seleccion)) seleccion = null;
  dibujar();
}

function existe(s) {
  return s.tipo === "nodo"
    ? !!posicion(s.nombre)
    : grafo.aristas.some((e) => mismaArista(e, s.a, s.b));
}

/** Ejecuta una llamada a la API mostrando los errores en pantalla. */
async function intentar(promesa, limpiar = true) {
  try {
    aplicar(await promesa, limpiar);
    mensaje("");
    return true;
  } catch (error) {
    mensaje(error.message, true);
    return false;
  }
}

// ---------------------------------------------------------------- dibujo
function crear(nombre, atributos, texto) {
  const nodo = document.createElementNS(NS, nombre);
  for (const [k, v] of Object.entries(atributos)) nodo.setAttribute(k, v);
  if (texto !== undefined) nodo.textContent = texto;
  lienzo.appendChild(nodo);
  return nodo;
}

function dibujar() {
  lienzo.innerHTML = "";
  const enRuta = new Set();
  rutaVisible.forEach((n, i) => {
    if (i) enRuta.add(rutaVisible[i - 1] + "|" + n);
  });
  for (const e of grafo.aristas) {
    const p1 = posicion(e.a),
      p2 = posicion(e.b);
    const resaltada =
      enRuta.has(e.a + "|" + e.b) || enRuta.has(e.b + "|" + e.a);
    const marcada =
      seleccion &&
      seleccion.tipo === "arista" &&
      mismaArista(e, seleccion.a, seleccion.b);
    const color = resaltada
      ? colorRuta
      : e.bloqueada
        ? COLOR.bloqueo
        : COLOR.arista;
    const atributos = {
      x1: p1.x,
      y1: p1.y,
      x2: p2.x,
      y2: p2.y,
      stroke: color,
      "stroke-width": resaltada ? 6 : marcada ? 4 : 2,
    };
    if (e.bloqueada) atributos["stroke-dasharray"] = "6 4";
    crear("line", atributos);
    const mx = (p1.x + p2.x) / 2,
      my = (p1.y + p2.y) / 2;
    crear("ellipse", {
      cx: mx,
      cy: my,
      rx: 16,
      ry: 9,
      fill: COLOR.etiqueta,
      stroke: color,
    });
    crear(
      "text",
      {
        x: mx,
        y: my + 3.5,
        "text-anchor": "middle",
        "font-size": 10,
        fill: COLOR.texto,
      },
      Number(e.peso),
    );
    // zona ancha e invisible para poder seleccionar la línea con el clic
    const zona = crear("line", {
      x1: p1.x,
      y1: p1.y,
      x2: p2.x,
      y2: p2.y,
      stroke: "transparent",
      "stroke-width": 14,
      "data-a": e.a,
      "data-b": e.b,
    });
    zona.style.cursor = "pointer";
  }
  for (const n of grafo.nodos) {
    const marcado =
      (seleccion &&
        seleccion.tipo === "nodo" &&
        seleccion.nombre === n.nombre) ||
      pendiente === n.nombre;
    const esOrigen = n.nombre === el("origen").value;
    const esDestino = n.nombre === el("destino").value;
    const relleno = esOrigen
      ? COLOR.origen
      : esDestino
        ? COLOR.destino
        : COLOR.nodo;
    const contorno = esOrigen || esDestino ? relleno : COLOR.anillo;
    const c = crear("circle", {
      cx: n.x,
      cy: n.y,
      r: RADIO,
      fill: relleno,
      stroke: marcado ? COLOR.seleccion : contorno,
      "stroke-width": 3,
      "data-nodo": n.nombre,
    });
    c.style.cursor = "pointer";
    crear(
      "text",
      {
        x: n.x,
        y: n.y + 4,
        "text-anchor": "middle",
        "font-size": 12,
        "font-weight": "bold",
        fill: esOrigen || esDestino ? "#10161d" : COLOR.texto,
        "pointer-events": "none",
      },
      n.nombre,
    );
  }
}

// ----------------------------------------------------------- interacción
function puntoSvg(evento) {
  const p = lienzo.createSVGPoint();
  p.x = evento.clientX;
  p.y = evento.clientY;
  const q = p.matrixTransform(lienzo.getScreenCTM().inverse());
  return { x: Math.round(q.x), y: Math.round(q.y) };
}

lienzo.addEventListener("pointerdown", async (evento) => {
  const { x, y } = puntoSvg(evento);
  const objetivo = evento.target;
  const nombre = objetivo.dataset.nodo;
  const m = modo();
  if (m === "nodo" && !nombre) {
    await intentar(api("POST", "/api/nodos", { x, y }));
  } else if (m === "arista" && nombre) {
    await conectarCon(nombre);
  } else if (m === "mover") {
    if (nombre) {
      seleccion = { tipo: "nodo", nombre };
      arrastre = nombre;
      lienzo.setPointerCapture(evento.pointerId);
    } else if (objetivo.dataset.a) {
      seleccion = {
        tipo: "arista",
        a: objetivo.dataset.a,
        b: objetivo.dataset.b,
      };
    } else {
      seleccion = null;
    }
  }
  dibujar();
});

lienzo.addEventListener("pointermove", (evento) => {
  if (!arrastre) return;
  const { x, y } = puntoSvg(evento);
  const nodo = posicion(arrastre);
  nodo.x = Math.max(0, Math.min(800, x));
  nodo.y = Math.max(0, Math.min(400, y));
  dibujar();
});

lienzo.addEventListener("pointerup", async () => {
  if (!arrastre) return;
  const nodo = posicion(arrastre);
  arrastre = null;
  // los resultados dependen de las posiciones (heurística de A*)
  await intentar(
    api("PATCH", `/api/nodos/${encodeURIComponent(nodo.nombre)}`, {
      x: nodo.x,
      y: nodo.y,
    }),
  );
});

async function conectarCon(nombre) {
  if (pendiente === null) {
    pendiente = nombre;
    return;
  }
  if (pendiente === nombre) return;
  const a = posicion(pendiente),
    b = posicion(nombre);
  const sugerido = Math.round(Math.hypot(a.x - b.x, a.y - b.y) * 10) / 10;
  const texto = await pedir(
    `Peso de ${pendiente}–${nombre}:`,
    sugerido,
    "number",
  );
  const origen = pendiente;
  pendiente = null;
  if (texto !== null) {
    await intentar(
      api("PUT", "/api/aristas", { a: origen, b: nombre, peso: Number(texto) }),
    );
  }
}

for (const radio of document.querySelectorAll("input[name=modo]")) {
  radio.addEventListener("change", () => {
    pendiente = null;
    document.querySelectorAll(".herramienta").forEach((item) => {
      item.classList.toggle(
        "activa",
        item.querySelector("input") === radio && radio.checked,
      );
    });
    dibujar();
  });
}

el("btn-editar").addEventListener("click", async () => {
  if (!seleccion) return mensaje("Seleccione un nodo o una conexión.", true);
  if (seleccion.tipo === "nodo") {
    const nuevo = await pedir("Nuevo nombre:", seleccion.nombre);
    if (nuevo === null) return;
    const viejo = seleccion.nombre;
    if (
      await intentar(
        api("PATCH", `/api/nodos/${encodeURIComponent(viejo)}`, {
          nuevo_nombre: nuevo.trim(),
        }),
      )
    ) {
      seleccion = { tipo: "nodo", nombre: nuevo.trim() };
      dibujar();
    }
  } else {
    const actual = grafo.aristas.find((e) =>
      mismaArista(e, seleccion.a, seleccion.b),
    );
    const peso = await pedir(
      `Nuevo peso de ${seleccion.a}–${seleccion.b}:`,
      actual.peso,
      "number",
    );
    if (peso !== null) {
      await intentar(
        api("PUT", "/api/aristas", {
          a: seleccion.a,
          b: seleccion.b,
          peso: Number(peso),
        }),
      );
    }
  }
});

el("btn-eliminar").addEventListener("click", async () => {
  if (!seleccion) return mensaje("Seleccione un nodo o una conexión.", true);
  const url =
    seleccion.tipo === "nodo"
      ? `/api/nodos/${encodeURIComponent(seleccion.nombre)}`
      : `/api/aristas/${encodeURIComponent(seleccion.a)}/` +
        encodeURIComponent(seleccion.b);
  if (await intentar(api("DELETE", url))) {
    seleccion = null;
    dibujar();
  }
});

el("btn-bloquear").addEventListener("click", async () => {
  if (!seleccion || seleccion.tipo !== "arista") {
    return mensaje("Seleccione una conexión (clic sobre la línea).", true);
  }
  const actual = grafo.aristas.find((e) =>
    mismaArista(e, seleccion.a, seleccion.b),
  );
  await intentar(
    api("PATCH", "/api/aristas/bloqueo", {
      a: seleccion.a,
      b: seleccion.b,
      bloqueada: !actual.bloqueada,
    }),
  );
});

el("btn-ejemplo").addEventListener("click", async () => {
  seleccion = pendiente = null;
  await intentar(api("POST", "/api/grafo/ejemplo"));
});
el("btn-limpiar").addEventListener("click", async () => {
  seleccion = pendiente = null;
  await intentar(api("DELETE", "/api/grafo"));
});
for (const id of ["origen", "destino"])
  el(id).addEventListener("change", dibujar);

// -------------------------------------------------------------- búsqueda
el("btn-ejecutar").addEventListener("click", async (evento) => {
  const boton = evento.currentTarget;
  const algoritmos = [...document.querySelectorAll(".alg:checked")].map(
    (c) => c.value,
  );
  if (!algoritmos.length) return mensaje("Marque al menos un algoritmo.", true);
  boton.disabled = true;
  mensaje("Midiendo…");
  try {
    resultados = await api("POST", "/api/rutas", {
      origen: el("origen").value,
      destino: el("destino").value,
      algoritmos,
    });
    mensaje("");
    mostrarResultados();
    elegirResultado(resultados[resultados.length - 1].algoritmo);
  } catch (error) {
    mensaje(error.message, true);
  }
  boton.disabled = false;
});

function mostrarResultados() {
  const cuerpo = el("tabla-resultados").querySelector("tbody");
  llenarTabla(
    cuerpo,
    resultados.map((r) => [
      r.algoritmo,
      r.ruta ? r.ruta.join(" → ") : "Sin ruta",
      {
        t:
          r.distancia === null
            ? "∞"
            : Number(r.distancia.toFixed(2)).toLocaleString("es-AR"),
        n: true,
      },
      { t: fmt(r.tiempo_ms, 4), n: true },
      { t: fmt(r.memoria_kb, 1) + " KB", n: true },
      { t: r.nodos_explorados, n: true },
    ]),
  );
  [...cuerpo.rows].forEach((fila, i) => {
    fila.classList.add("elegible");
    fila.addEventListener("click", () =>
      elegirResultado(resultados[i].algoritmo),
    );
  });
  dibujarGraficoRutas();
}

/** Gráfico SVG de barras horizontales alimentado por las mediciones reales. */
function dibujarGraficoRutas() {
  const contenedor = el("grafico-rutas");
  if (!resultados.length) {
    contenedor.innerHTML =
      '<p class="nota">Ejecute una búsqueda para generar el gráfico.</p>';
    return;
  }
  const filas = resultados.filter((r) => Number.isFinite(r.tiempo_ms));
  const maximo = Math.max(...filas.map((r) => r.tiempo_ms), 0.0001);
  const ancho = 700,
    altoFila = 42,
    margen = 130,
    anchoBarra = 500;
  let svg = `<svg viewBox="0 0 ${ancho} ${filas.length * altoFila + 18}" role="img" aria-label="Comparación de tiempo por algoritmo">`;
  filas.forEach((r, i) => {
    const y = i * altoFila + 8;
    const w = Math.max(2, (r.tiempo_ms / maximo) * anchoBarra);
    const color = COLORES[r.algoritmo] || COLOR.anillo;
    svg += `<text x="${margen - 10}" y="${y + 19}" text-anchor="end" font-size="13" fill="currentColor">${esc(r.algoritmo)}</text>`;
    svg += `<rect x="${margen}" y="${y}" width="${w}" height="25" rx="4" fill="${color}"><title>${esc(r.algoritmo)}: ${fmt(r.tiempo_ms, 4)} ms</title></rect>`;
    svg += `<text x="${Math.min(margen + w + 8, ancho - 58)}" y="${y + 17}" font-size="12" fill="currentColor">${fmt(r.tiempo_ms, 4)} ms</text>`;
  });
  contenedor.innerHTML = svg + "</svg>";
}

function elegirResultado(algoritmo) {
  const indice = resultados.findIndex((r) => r.algoritmo === algoritmo);
  rutaVisible = resultados[indice].ruta || [];
  colorRuta = COLORES[algoritmo];
  [...el("tabla-resultados").querySelector("tbody").rows].forEach((fila, i) =>
    fila.classList.toggle("elegida", i === indice),
  );
  dibujar();
}

// ------------------------------------------------------------------ inicio
(async function iniciar() {
  const info = await api("GET", "/api/informacion");
  llenarTabla(
    el("tabla-info").querySelector("tbody"),
    info.map((f) => [
      f.algoritmo,
      {
        h: f.estructuras
          .split(", ")
          .map(
            (nombre) =>
              `<span class="etiqueta-estructura">${esc(nombre)}</span>`,
          )
          .join(" "),
      },
      f.funcionamiento,
      f.complejidad_temporal,
      f.complejidad_espacial,
    ]),
  );
  await intentar(api("GET", "/api/grafo"));
  el("origen").value = grafo.nodos[0] ? grafo.nodos[0].nombre : "";
  el("destino").value = grafo.nodos.length
    ? grafo.nodos[grafo.nodos.length - 1].nombre
    : "";
  dibujar();
})();
