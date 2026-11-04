/* Ventana Optimización: herramientas que detectan código redundante. */
const HERRAMIENTAS = ["ruff", "vulture", "pylint", "radon", "cobertura"];
const ETIQUETA = {
  ruff: "hallazgos",
  vulture: "elementos sin usar",
  pylint: "bloques repetidos",
  radon: "funciones sobre el límite",
  cobertura: "líneas sin ejecutar",
};

/* ---------- Interpretación automática de cada herramienta ---------- */

/** Cómo se reparte el total entre categorías, sin presuponer que una predomine. */
function reparto(pares, total, que) {
  if (pares.length < 2) return "";
  const [[a, na], [b, nb]] = pares;
  if (casiIguales(na, nb)) {
    return `Por ${que}, ${a} (${na}) y ${b} (${nb}) están a la par: ninguno predomina.`;
  }
  return `Por ${que}, el mayor recuento es ${a}: ${na} de ${total} (${porcentajeDe(na, total)}).`;
}

const archivosAfectados = (filas) => new Set(filas.map((f) => f.archivo)).size;
const valorFicha = (datos, prefijo) =>
  datos.fichas.find((f) => f.titulo.startsWith(prefijo));

function analizarRuff(datos) {
  if (!datos.total) {
    return "Ruff no halló hallazgos con las reglas seleccionadas. Eso no descarta otro código redundante: solo se revisaron esas reglas.";
  }
  return [
    `${pluralizar(datos.total, "hallazgo", "hallazgos")} en ${pluralizar(archivosAfectados(datos.filas), "archivo", "archivos")}.`,
    reparto(contarPor(datos.filas, (f) => f.archivo), datos.total, "archivo"),
    reparto(contarPor(datos.filas, (f) => f.regla), datos.total, "regla"),
    "Cada fila es un candidato a revisar antes de modificar el código.",
  ].filter(Boolean).join(" ");
}

function analizarVulture(datos) {
  if (!datos.total) {
    return "Vulture no halló elementos sin usar con la configuración del proyecto. Es un análisis estático: no ve usos dinámicos ni garantiza que no quede código muerto.";
  }
  const seguros = datos.filas.filter((f) => parseInt(f.regla, 10) >= 100).length;
  const resto = datos.total - seguros;
  const frases = [
    `${pluralizar(datos.total, "elemento", "elementos")} sin usar en ${pluralizar(archivosAfectados(datos.filas), "archivo", "archivos")}.`,
    `${seguros} con confianza del 100 % y ${resto} con confianza menor.`,
  ];
  if (resto) {
    frases.push("Con menor confianza es más probable un uso que Vulture no detecta (decoradores, nombres dinámicos): conviene verificarlo antes de borrar.");
  }
  return frases.join(" ");
}

function analizarPylint(datos) {
  if (!datos.total) {
    return "Pylint no halló bloques repetidos entre archivos. Solo detecta tramos de líneas similares, no lógica equivalente escrita de otra forma.";
  }
  return [
    `${pluralizar(datos.total, "aparición", "apariciones")} de bloques repetidos en ${pluralizar(archivosAfectados(datos.filas), "archivo", "archivos")}; cada fila es una aparición y un mismo bloque ocupa al menos dos.`,
    reparto(contarPor(datos.filas, (f) => f.archivo), datos.total, "archivo"),
    "Unificarlos solo conviene si representan la misma lógica; a veces la repetición es casual.",
  ].filter(Boolean).join(" ");
}

function analizarRadon(datos) {
  const promedio = valorFicha(datos, "complejidad promedio")?.valor;
  const analizadas = valorFicha(datos, "funciones analizadas")?.valor;
  const frases = [];
  if (datos.cumple) {
    frases.push(`Ninguna de las ${analizadas ?? "?"} funciones analizadas supera el límite del criterio.`);
  } else {
    frases.push(`${datos.total} de ${analizadas ?? "?"} funciones ${datos.total === 1 ? "supera" : "superan"} el límite del criterio.`);
  }
  const [primera, segunda] = datos.filas;
  if (primera) {
    const compleja = (f) => Number(/\((\d+)\)/.exec(f.regla)?.[1]);
    const c1 = compleja(primera);
    let frase = `La más compleja es ${primera.mensaje} (complejidad ${c1}${promedio ? `, promedio general ${fmt(promedio, 1)}` : ""}).`;
    if (segunda && casiIguales(c1, compleja(segunda))) {
      frase += ` ${segunda.mensaje} tiene ${compleja(segunda)}: la diferencia es mínima y no destaca una sola.`;
    }
    frases.push(frase + " La tabla muestra solo las cinco más complejas.");
  }
  const mantenibilidad = valorFicha(datos, "mantenibilidad mínima");
  if (mantenibilidad) {
    const archivo = /\((.*)\)$/.exec(mantenibilidad.titulo)?.[1] || "el archivo más bajo";
    const v = Number(mantenibilidad.valor);
    const rango = v >= 20 ? "A (20 o más)" : v >= 10 ? "B (10 a 19)" : "C (menos de 10)";
    frases.push(`El menor índice de mantenibilidad es ${fmt(v, 1)} en ${archivo}: rango ${rango} de Radon.`);
  }
  return frases.join(" ");
}

function analizarCobertura(datos) {
  if (!datos.total && !datos.filas.length) {
    return "Las pruebas ejecutaron todas las líneas medidas.";
  }
  const lineas = (f) => {
    const m = /(\d+)-(\d+)/.exec(f.mensaje);
    return m ? Number(m[2]) - Number(m[1]) + 1 : 1;
  };
  return [
    `${pluralizar(datos.total, "línea", "líneas")} sin ejecutar, en ${pluralizar(datos.filas.length, "tramo", "tramos")} de ${pluralizar(archivosAfectados(datos.filas), "archivo", "archivos")}.`,
    reparto(contarPor(datos.filas, (f) => f.archivo, lineas), datos.total, "archivo (en líneas)"),
    "Es informativo: un tramo sin ejecutar puede ser código muerto, una rama de error o código sin probar, y no es un defecto por sí solo.",
  ].filter(Boolean).join(" ");
}

const ANALIZAR = {
  ruff: analizarRuff,
  vulture: analizarVulture,
  pylint: analizarPylint,
  radon: analizarRadon,
  cobertura: analizarCobertura,
};

function mostrar(nombre, datos, origen = "") {
  const clase = datos.cumple === null ? "" : datos.cumple ? "ok" : "mal";
  const veredicto =
    datos.cumple === null
      ? ""
      : datos.cumple
        ? ' · <span class="ok">cumple</span>'
        : ' · <span class="mal">no cumple</span>';
  el(`res-${nombre}`).innerHTML =
    ficha(`${datos.herramienta}: ${ETIQUETA[nombre]}`, datos.total, clase) +
    datos.fichas.map((f) => ficha(f.titulo, f.valor)).join("");
  el(`criterio-${nombre}`).innerHTML =
    `Criterio: ${esc(datos.criterio)}${veredicto}` +
    (origen ? ` · <small>${esc(origen)}</small>` : "");
  el(`analisis-${nombre}`).textContent = ANALIZAR[nombre](datos);
  const tbody = el(`tabla-${nombre}`).querySelector("tbody");
  if (!datos.filas.length) {
    tbody.innerHTML = '<tr><td colspan="4">Sin hallazgos.</td></tr>';
    return;
  }
  llenarTabla(
    tbody,
    datos.filas.map((f) => [
      f.archivo,
      { t: f.linea, n: true },
      f.regla,
      f.mensaje,
    ]),
  );
}

async function analizar() {
  const boton = el("btn-limpieza"),
    estado = el("estado-limpieza");
  boton.disabled = true;
  estado.className = "estado";
  const fallidas = [];
  for (const nombre of HERRAMIENTAS) {
    estado.textContent = `Ejecutando ${nombre}…`;
    try {
      const resultado = await api("POST", `/api/optimizacion/${nombre}`);
      mostrar(nombre, resultado);
      guardarResultado(`optimizacion:${nombre}`, resultado);
    } catch (error) {
      fallidas.push(nombre);
      el(`res-${nombre}`).textContent = "";
      el(`analisis-${nombre}`).textContent = "";
      el(`tabla-${nombre}`).querySelector("tbody").innerHTML =
        '<tr><td colspan="4">No hay resultados de esta solicitud.</td></tr>';
      el(`criterio-${nombre}`).innerHTML =
        `<span class="mal">${esc(error.message)}</span>`;
    }
  }
  estado.textContent = fallidas.length
    ? `Análisis terminado. Sin resultado actual: ${fallidas.join(", ")}.`
    : "Análisis completado.";
  boton.disabled = false;
}

for (const nombre of HERRAMIENTAS) {
  const guardado = leerResultado(`optimizacion:${nombre}`);
  if (guardado?.datos) {
    mostrar(nombre, guardado.datos, etiquetaResultadoGuardado(guardado));
  }
}

el("btn-limpieza").addEventListener("click", analizar);
// Las herramientas se ejecutan únicamente al solicitar un nuevo análisis.
