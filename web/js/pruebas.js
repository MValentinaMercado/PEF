/* Ventana 3: ejecuta la suite de pruebas y muestra el resultado. */
const el = (id) => document.getElementById(id);
let datos = null;

const ETIQUETA = {
  ok: ["ok", "aprobada"],
  falló: ["mal", "falló"],
  error: ["mal", "error"],
  omitida: ["", "omitida"],
};

function ficha(titulo, valor, clase = "") {
  return (
    `<div class="ficha"><b class="${clase}">${valor}</b>` +
    `${esc(titulo)}</div>`
  );
}

function mostrar() {
  const malas = datos.fallidas + datos.errores;
  el("resumen").innerHTML =
    ficha("pruebas", datos.total) +
    ficha("aprobadas", datos.aprobadas, "ok") +
    ficha("no aprobadas", malas, malas ? "mal" : "ok") +
    ficha("omitidas", datos.omitidas) +
    ficha("segundos", fmt(datos.segundos, 2));

  const tipos = [...new Set(datos.pruebas.map((p) => p.tipo))];
  llenarTabla(
    el("tabla-tipos").querySelector("tbody"),
    tipos.map((t) => {
      const grupo = datos.pruebas.filter((p) => p.tipo === t);
      const buenas = grupo.filter((p) => p.resultado === "ok").length;
      return [
        t,
        { t: grupo.length, n: true },
        { t: buenas, n: true },
        { t: grupo.length - buenas, n: true },
      ];
    }),
  );

  const filtro = el("filtro-tipo"),
    previo = filtro.value;
  filtro.innerHTML =
    '<option value="">Todos</option>' +
    tipos.map((t) => `<option>${esc(t)}</option>`).join("");
  filtro.value = tipos.includes(previo) ? previo : "";
  detalle();
  el("salida").textContent = datos.salida;
}

function detalle() {
  const tipo = el("filtro-tipo").value,
    soloFallas = el("solo-fallas").checked;
  const filas = datos.pruebas.filter(
    (p) => (!tipo || p.tipo === tipo) && (!soloFallas || p.resultado !== "ok"),
  );
  llenarTabla(
    el("tabla-pruebas").querySelector("tbody"),
    filas.map((p) => {
      const [clase, texto] = ETIQUETA[p.resultado];
      return [
        p.tipo,
        p.grupo,
        p.nombre,
        {
          h:
            `<span class="${clase}">${texto}</span>` +
            (p.detalle ? `<br><small>${esc(p.detalle)}</small>` : ""),
        },
        { t: fmt(p.segundos, 3), n: true },
      ];
    }),
  );
}

async function ejecutar() {
  const boton = el("btn-pruebas"),
    estado = el("estado-pruebas");
  boton.disabled = true;
  estado.className = "estado";
  estado.textContent = "Ejecutando pytest…";
  try {
    datos = await api("POST", "/api/pruebas/ejecutar");
    estado.textContent = "";
    mostrar();
  } catch (error) {
    estado.className = "estado error";
    estado.textContent = error.message;
  }
  boton.disabled = false;
}

el("btn-pruebas").addEventListener("click", ejecutar);
el("filtro-tipo").addEventListener("change", () => datos && detalle());
el("solo-fallas").addEventListener("change", () => datos && detalle());
ejecutar(); // al abrir la ventana se ejecutan solas
