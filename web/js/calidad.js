/* Ventana 5: análisis estático (Ruff), cobertura y condiciones de calidad. */
const el = (id) => document.getElementById(id);
let condiciones = { lint: [], cobertura: [] };
let lint = null;
let cobertura = null;

function ficha(titulo, valor, clase = "") {
  return (
    `<div class="ficha"><b class="${clase}">${valor}</b>` +
    `${esc(titulo)}</div>`
  );
}

function marca(ok) {
  return ok
    ? '<span class="ok">cumple</span>'
    : '<span class="mal">no cumple</span>';
}

function mostrarCondiciones() {
  const todas = [...condiciones.lint, ...condiciones.cobertura];
  const pendientes = !condiciones.lint.length || !condiciones.cobertura.length;
  const falla = todas.some((c) => !c.ok);
  el("veredicto").innerHTML =
    pendientes && !falla
      ? ficha("calculando…", "…")
      : ficha(
          falla ? "el pipeline fallaría" : "el pipeline aprobaría",
          falla ? "NO APROBADO" : "APROBADO",
          falla ? "mal" : "ok",
        );
  llenarTabla(
    el("tabla-condiciones").querySelector("tbody"),
    todas.map((c) => [c.nombre, { h: marca(c.ok) }, c.detalle]),
  );
}

function mostrarLint() {
  const { calidad, sin_formato: sinFormato } = lint;
  const cubierto = cobertura ? cobertura.cobertura.porcentaje : null;
  el("resumen").innerHTML =
    ficha(lint.herramienta, calidad.total, calidad.total ? "mal" : "ok") +
    ficha("sin formato", sinFormato.length, sinFormato.length ? "mal" : "ok") +
    (cubierto === null
      ? ""
      : ficha("cobertura %", fmt(cubierto, 1)) +
        ficha("pruebas", cobertura.pruebas.total));
  llenarTabla(
    el("tabla-reglas").querySelector("tbody"),
    Object.entries(calidad.por_regla).map(([regla, n]) => [
      regla,
      { t: n, n: true },
    ]),
  );
  llenarTabla(
    el("tabla-hallazgos").querySelector("tbody"),
    calidad.hallazgos.map((h) => [
      h.archivo,
      { t: h.linea, n: true },
      h.regla,
      h.mensaje,
    ]),
  );
  el("sin-formato").textContent = sinFormato.length
    ? sinFormato.join("\n")
    : "Todos los archivos cumplen el formato.";
}

function mostrarCobertura() {
  llenarTabla(
    el("tabla-cobertura").querySelector("tbody"),
    cobertura.cobertura.archivos.map((a) => [
      a.archivo,
      { t: a.sentencias, n: true },
      { t: a.faltan, n: true },
      { t: fmt(a.porcentaje, 1) + " %", n: true },
    ]),
  );
  el("salida").textContent = cobertura.salida;
}

async function analizar() {
  const boton = el("btn-calidad"),
    estado = el("estado-calidad");
  boton.disabled = true;
  estado.className = "estado";
  condiciones = { lint: [], cobertura: [] };
  lint = cobertura = null;
  mostrarCondiciones();
  try {
    estado.textContent = "Ejecutando Ruff…";
    lint = await api("POST", "/api/calidad/lint");
    condiciones.lint = lint.condiciones;
    mostrarLint();
    mostrarCondiciones();
    estado.textContent = "Midiendo la cobertura de las pruebas…";
    cobertura = await api("POST", "/api/calidad/cobertura");
    condiciones.cobertura = cobertura.condiciones;
    mostrarLint();
    mostrarCobertura();
    mostrarCondiciones();
    estado.textContent = "";
  } catch (error) {
    estado.className = "estado error";
    estado.textContent = error.message;
  }
  boton.disabled = false;
}

el("btn-calidad").addEventListener("click", analizar);
analizar(); // al abrir la ventana se ejecuta sola
