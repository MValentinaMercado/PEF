/* Ventana 3: herramientas que detectan código redundante. */
const el = (id) => document.getElementById(id);
const HERRAMIENTAS = ["ruff", "vulture", "pylint", "radon", "cobertura"];
const ETIQUETA = {
  ruff: "hallazgos",
  vulture: "elementos sin usar",
  pylint: "bloques repetidos",
  radon: "funciones sobre el límite",
  cobertura: "líneas sin ejecutar",
};

function ficha(titulo, valor, clase = "") {
  return (
    `<div class="ficha"><b class="${clase}">${esc(valor)}</b>` +
    `${esc(titulo)}</div>`
  );
}

function mostrar(nombre, datos) {
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
    `Criterio: ${esc(datos.criterio)}${veredicto}`;
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
  for (const nombre of HERRAMIENTAS) {
    estado.textContent = `Ejecutando ${nombre}…`;
    try {
      mostrar(nombre, await api("POST", `/api/optimizacion/${nombre}`));
    } catch (error) {
      el(`criterio-${nombre}`).innerHTML =
        `<span class="mal">${esc(error.message)}</span>`;
    }
  }
  estado.textContent = "";
  boton.disabled = false;
}

el("btn-limpieza").addEventListener("click", analizar);
analizar(); // al abrir la ventana se ejecuta sola
