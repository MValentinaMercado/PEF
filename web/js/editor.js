/* Ventana 1: editor del grafo (SVG) y búsqueda de rutas. */
const NS = "http://www.w3.org/2000/svg";
const RADIO = 16;
const COLOR = {
  anillo: "#d6d3ce",
  ruta: "#f28c28",
};

const lienzo = el("lienzo");
let grafo = { nodos: [], aristas: [] };
let seleccion = null; // {tipo: "nodo", nombre} | {tipo: "arista", a, b}
let pendiente = null; // primer nodo de una conexión a medio crear
let resultados = []; // filas devueltas por /api/rutas
let rutaVisible = [];
let algoritmoElegido = null; // algoritmo cuya ruta se muestra
let animarRuta = false; // dibuja la ruta con animación solo al elegirla
let arrastre = null; // {nombre} mientras se mueve un nodo
const CLAVE_GUARDADO = "editor";

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
    algoritmoElegido = null;
    guardarResultado(CLAVE_GUARDADO, null);
    el("estado-resultados").textContent = "";
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

/** Dibuja una conexión: línea, etiqueta de peso y zona de clic. */
function dibujarArista(e, resaltada, nueva) {
  const p1 = posicion(e.a),
    p2 = posicion(e.b);
  const marcada =
    seleccion &&
    seleccion.tipo === "arista" &&
    mismaArista(e, seleccion.a, seleccion.b);
  const estado = resaltada ? "ruta" : e.bloqueada ? "bloqueada" : "";
  const clases = [
    "arista",
    estado,
    marcada ? "marcada" : "",
    nueva ? "nueva" : "",
  ]
    .filter(Boolean)
    .join(" ");
  crear("line", {
    class: clases,
    x1: p1.x,
    y1: p1.y,
    x2: p2.x,
    y2: p2.y,
    pathLength: 1,
  });
  const mx = (p1.x + p2.x) / 2,
    my = (p1.y + p2.y) / 2;
  crear("rect", {
    class: "peso-caja " + estado,
    x: mx - 16,
    y: my - 9,
    width: 32,
    height: 18,
    rx: 9,
  });
  crear(
    "text",
    {
      class: "peso-texto " + estado,
      x: mx,
      y: my + 3.5,
      "text-anchor": "middle",
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

function dibujar() {
  lienzo.innerHTML = "";
  const nuevaRuta = animarRuta;
  animarRuta = false;
  const enRuta = new Set();
  rutaVisible.forEach((n, i) => {
    if (i) enRuta.add(rutaVisible[i - 1] + "|" + n);
  });
  const nodosRuta = new Set(rutaVisible);
  const esDeRuta = (e) =>
    enRuta.has(e.a + "|" + e.b) || enRuta.has(e.b + "|" + e.a);

  // Capas: primero todo el contexto en gris, la ruta por encima y los nodos arriba.
  for (const e of grafo.aristas)
    if (!esDeRuta(e)) dibujarArista(e, false, false);
  for (const e of grafo.aristas)
    if (esDeRuta(e)) dibujarArista(e, true, nuevaRuta);

  const origen = el("origen").value,
    destino = el("destino").value;
  for (const n of grafo.nodos) {
    const marcado =
      (seleccion &&
        seleccion.tipo === "nodo" &&
        seleccion.nombre === n.nombre) ||
      pendiente === n.nombre;
    const esOrigen = n.nombre === origen;
    const esDestino = n.nombre === destino;
    const estado = esOrigen
      ? "origen"
      : esDestino
        ? "destino"
        : nodosRuta.has(n.nombre)
          ? "en-ruta"
          : "";
    if (esOrigen || esDestino) {
      crear("circle", {
        class: "halo " + (esOrigen ? "origen" : "destino"),
        cx: n.x,
        cy: n.y,
        r: RADIO + 7,
      });
    }
    const c = crear("circle", {
      class: ["nodo", estado, marcado ? "seleccionado" : ""]
        .filter(Boolean)
        .join(" "),
      cx: n.x,
      cy: n.y,
      r: RADIO,
      "data-nodo": n.nombre,
    });
    c.style.cursor = "pointer";
    crear(
      "text",
      {
        class:
          "nombre-nodo" +
          (esOrigen || esDestino
            ? " claro"
            : estado === "en-ruta"
              ? " ruta"
              : ""),
        x: n.x,
        y: n.y + 4,
        "text-anchor": "middle",
      },
      n.nombre,
    );
    if (esOrigen || esDestino) {
      // rótulo sobre el nodo; si no cabe arriba, debajo
      const arriba = n.y > 46;
      crear(
        "text",
        {
          class: "rotulo",
          x: n.x,
          y: arriba ? n.y - RADIO - 12 : n.y + RADIO + 20,
          "text-anchor": "middle",
        },
        esOrigen && esDestino
          ? "Origen y destino"
          : esOrigen
            ? "Origen"
            : "Destino",
      );
    }
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
  if (!seleccion) return mensaje("Seleccioná un nodo o una conexión.", true);
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
  if (!seleccion) return mensaje("Seleccioná un nodo o una conexión.", true);
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
    return mensaje("Seleccioná una conexión (clic sobre la línea).", true);
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
  if (!algoritmos.length) return mensaje("Marcá al menos un algoritmo.", true);
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
    guardarResultado(CLAVE_GUARDADO, {
      origen: el("origen").value,
      destino: el("destino").value,
      grafo,
      resultados,
    });
    el("estado-resultados").textContent = "Ejecución completada ahora.";
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
  el("analisis-rutas").textContent = analizarRutas(resultados, grafo);
  dibujarGraficoRutas();
  pintarTarjetaRuta();
}

const formatoDistancia = (d) => Number(d.toFixed(2)).toLocaleString("es-AR");
/** Distancia y cantidad de conexiones de las rutas encontradas. */
function compararRutas(conRuta) {
  const distancias = conMenor(conRuta, (r) => r.distancia, false);
  const saltos = conMenor(conRuta, (r) => r.ruta.length - 1, false);
  const nombresDe = (grupo) => grupo.filas.map((r) => r.algoritmo);
  const iguales = distancias.filas.length === conRuta.length;
  const mismoCamino = new Set(conRuta.map((r) => r.ruta.join(">"))).size === 1;
  if (iguales && mismoCamino) {
    return `Todos encontraron el mismo camino, de distancia ${formatoDistancia(distancias.minimo)}.`;
  }
  if (iguales) {
    return `Todos llegaron a la misma distancia (${formatoDistancia(distancias.minimo)}) por caminos distintos.`;
  }
  const frases = [
    `La menor distancia (${formatoDistancia(distancias.minimo)}) la logran ${listar(nombresDe(distancias))}; ${listar(conRuta.filter((r) => !distancias.filas.includes(r)).map((r) => `${r.algoritmo} recorre ${formatoDistancia(r.distancia)}`))}.`,
  ];
  if (saltos.filas.some((r) => !distancias.filas.includes(r))) {
    frases.push(`${listar(nombresDe(saltos))} usa${saltos.filas.length > 1 ? "n" : ""} menos conexiones (${saltos.minimo}), pero eso no implica menor distancia.`);
  }
  return frases.join(" ");
}

/** Interpreta la tabla de comparación a partir de las filas recibidas o restauradas. */
function analizarRutas(filas, grafoActual) {
  if (!filas.length) return "";
  const conRuta = filas.filter((r) => r.ruta);
  if (!conRuta.length) {
    return "Ningún algoritmo encontró ruta: con las conexiones habilitadas, origen y destino no están conectados (las bloqueadas no cuentan).";
  }
  const frases = [];
  if (conRuta.length < filas.length) {
    const sin = filas.filter((r) => !r.ruta).map((r) => r.algoritmo);
    frases.push(`${listar(sin)} no encontró${sin.length > 1 ? "n" : ""} ruta, a diferencia del resto.`);
  }
  if (filas.length === 1) {
    frases.push(`Con un solo algoritmo no hay comparación posible: marcá más para contrastar ${filas[0].algoritmo}.`);
    return frases.join(" ");
  }
  if (conRuta.length > 1) frases.push(compararRutas(conRuta));
  frases.push(compararMagnitud(filas, (r) => r.nodos_explorados, "Nodos explorados", (n) => String(n)));
  frases.push(compararMagnitud(filas, (r) => r.tiempo_ms, "Tiempo", (n) => `${fmt(n, 4)} ms`));
  frases.push(compararMagnitud(filas, (r) => r.memoria_kb, "Memoria", (n) => `${fmt(n, 1)} KB`));
  frases.push(
    `Con ${pluralizar(grafoActual.nodos.length, "nodo", "nodos")} las diferencias son pequeñas y pueden variar entre ejecuciones; los grafos grandes se comparan en Análisis.`,
  );
  return frases.join(" ");
}

/** Gráfico SVG de barras horizontales alimentado por las mediciones reales. */
function dibujarGraficoRutas() {
  const contenedor = el("grafico-rutas");
  if (!resultados.length) {
    contenedor.innerHTML =
      '<p class="nota">Ejecutá una búsqueda para generar el gráfico.</p>';
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

function elegirResultado(algoritmo, animar = true) {
  const indice = resultados.findIndex((r) => r.algoritmo === algoritmo);
  rutaVisible = resultados[indice].ruta || [];
  algoritmoElegido = algoritmo;
  animarRuta = animar;
  [...el("tabla-resultados").querySelector("tbody").rows].forEach((fila, i) =>
    fila.classList.toggle("elegida", i === indice),
  );
  pintarTarjetaRuta();
  dibujar();
}

/** Tarjeta con el detalle de la ruta elegida (mismos datos que la tabla). */
function pintarTarjetaRuta() {
  const caja = el("detalle-ruta");
  const actual = resultados.find((r) => r.algoritmo === algoritmoElegido);
  if (!resultados.length || !actual) {
    caja.innerHTML =
      '<p class="ruta-vacia">Elegí un origen y un destino y ejecutá la búsqueda para ver acá la ruta.</p>';
    return;
  }
  const selector =
    resultados.length > 1
      ? '<div class="selector-algoritmo" role="group" aria-label="Algoritmo mostrado">' +
        resultados
          .map(
            (r) =>
              `<button type="button" data-algoritmo="${esc(r.algoritmo)}" aria-pressed="${r.algoritmo === actual.algoritmo}">${esc(r.algoritmo)}</button>`,
          )
          .join("") +
        "</div>"
      : `<div class="selector-algoritmo"><button type="button" aria-pressed="true" disabled>${esc(actual.algoritmo)}</button></div>`;
  let cuerpo;
  if (!actual.ruta) {
    cuerpo = '<p class="ruta-sin">No hay ruta entre esos nodos.</p>';
  } else {
    const ultimo = actual.ruta.length - 1;
    const pasos = actual.ruta
      .map(
        (n, i) =>
          `<span class="paso${i === 0 ? " origen" : i === ultimo ? " destino" : ""}">${esc(n)}</span>`,
      )
      .join('<span class="union" aria-hidden="true"></span>');
    const distancia =
      actual.distancia === null
        ? "∞"
        : Number(actual.distancia.toFixed(2)).toLocaleString("es-AR");
    cuerpo =
      `<div class="ruta-secuencia" aria-label="Ruta: ${esc(actual.ruta.join(" a "))}">${pasos}</div>` +
      `<p class="ruta-distancia"><b>${esc(distancia)}</b>distancia total</p>`;
  }
  caja.innerHTML =
    selector +
    cuerpo +
    '<dl class="ruta-metricas">' +
    `<div><dt>Tiempo</dt><dd>${fmt(actual.tiempo_ms, 4)} ms</dd></div>` +
    `<div><dt>Memoria</dt><dd>${fmt(actual.memoria_kb, 1)} KB</dd></div>` +
    `<div><dt>Nodos explorados</dt><dd>${esc(actual.nodos_explorados)}</dd></div>` +
    "</dl>";
  caja
    .querySelectorAll("button[data-algoritmo]")
    .forEach((b) =>
      b.addEventListener("click", () => elegirResultado(b.dataset.algoritmo)),
    );
}

// ------------------------------------------------------------------ inicio
/** Restaura la última ejecución guardada si sigue siendo válida para el grafo actual. */
function restaurarResultados() {
  const guardado = leerResultado(CLAVE_GUARDADO);
  const previo = guardado?.datos;
  if (!previo?.resultados?.length) return;
  const nombres = grafo.nodos.map((n) => n.nombre);
  const vigente =
    JSON.stringify(previo.grafo) === JSON.stringify(grafo) &&
    nombres.includes(previo.origen) &&
    nombres.includes(previo.destino);
  if (!vigente) {
    guardarResultado(CLAVE_GUARDADO, null);
    return;
  }
  el("origen").value = previo.origen;
  el("destino").value = previo.destino;
  resultados = previo.resultados;
  const usados = new Set(resultados.map((r) => r.algoritmo));
  document.querySelectorAll(".alg").forEach((c) => (c.checked = usados.has(c.value)));
  mostrarResultados();
  elegirResultado(resultados[resultados.length - 1].algoritmo, false);
  el("estado-resultados").textContent = etiquetaResultadoGuardado(guardado);
}

(async function iniciar() {
  // La carga inicial no borra la última ejecución guardada.
  await intentar(api("GET", "/api/grafo"), false);
  el("origen").value = grafo.nodos[0] ? grafo.nodos[0].nombre : "";
  el("destino").value = grafo.nodos.length
    ? grafo.nodos[grafo.nodos.length - 1].nombre
    : "";
  restaurarResultados();
  if (!resultados.length) mostrarResultados();
  dibujar();
})().catch((error) => mensaje(error.message, true));
