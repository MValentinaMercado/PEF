/* Ventana 5: estado del proyecto en SonarQube Cloud y en GitHub Actions. */

function mostrar(datos) {
  const aprobado = datos.estado === "OK";
  const sinDatos = datos.estado === "NONE";
  el("veredicto").innerHTML = ficha(
    `Quality Gate de ${datos.proyecto}`,
    sinDatos ? "SIN ANÁLISIS" : aprobado ? "APROBADO" : "NO APROBADO",
    sinDatos ? "" : aprobado ? "ok" : "mal",
  );
  const enlace = el("enlace-panel");
  enlace.href = datos.panel;
  enlace.hidden = false;
  llenarTabla(
    el("tabla-condiciones").querySelector("tbody"),
    datos.condiciones.map((c) => [
      c.nombre,
      {
        h: c.ok
          ? '<span class="ok">cumple</span>'
          : '<span class="mal">no cumple</span>',
      },
      { t: c.valor, n: true },
      c.exigencia,
    ]),
  );
  el("medidas").innerHTML = datos.medidas
    .map((m) => ficha(m.nombre, m.valor))
    .join("");
}

async function actualizar() {
  const boton = el("btn-calidad"),
    estado = el("estado-calidad");
  boton.disabled = true;
  estado.className = "estado";
  estado.textContent = "Consultando SonarQube Cloud…";
  try {
    mostrar(await api("GET", "/api/calidad/sonar"));
    estado.textContent = "";
  } catch (error) {
    estado.className = "estado error";
    estado.textContent = error.message;
  }
  boton.disabled = false;
}

el("btn-calidad").addEventListener("click", actualizar);
void actualizar(); // al abrir la ventana se consulta sola

/* ---------- Pipeline de CI en GitHub Actions ---------- */

const CLASE_ESTADO = {
  aprobado: "ok",
  rechazado: "mal",
  cancelado: "mal",
};

const estadoHtml = (estado) =>
  `<span class="${CLASE_ESTADO[estado] || ""}">${esc(estado)}</span>`;

const duracion = (segundos) => {
  if (segundos === null || segundos === undefined) return "—";
  const total = Math.round(segundos);
  return total >= 60
    ? `${Math.floor(total / 60)} min ${total % 60} s`
    : `${total} s`;
};

const enlaceHtml = (url, texto) =>
  url
    ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(texto)}</a>`
    : "—";

function mostrarCi(datos) {
  const ultima = datos.ultima;
  el("veredicto-ci").innerHTML = ficha(
    `Corrida #${ultima.numero} en ${datos.rama}`,
    ultima.estado.toUpperCase(),
    CLASE_ESTADO[ultima.estado] || "",
  );
  el("conclusion-ci").textContent = datos.conclusion;
  const enlace = el("enlace-ci");
  enlace.href = datos.panel;
  enlace.hidden = false;
  llenarTabla(
    el("tabla-etapas").querySelector("tbody"),
    datos.etapas.map((e) => [
      e.nombre,
      { h: estadoHtml(e.estado) },
      duracion(e.segundos),
      e.paso_fallido || "—",
      { h: enlaceHtml(e.url, "ver registro") },
    ]),
  );
  llenarTabla(
    el("tabla-historial").querySelector("tbody"),
    datos.historial.map((c) => [
      { h: enlaceHtml(c.url, "#" + c.numero) },
      { h: estadoHtml(c.estado) },
      { h: `<code>${esc(c.commit)}</code>` },
      c.titulo,
      c.evento,
      duracion(c.segundos),
    ]),
  );
}

async function actualizarCi() {
  const boton = el("btn-ci"),
    estado = el("estado-ci");
  boton.disabled = true;
  estado.className = "estado";
  estado.textContent = "Consultando GitHub Actions…";
  try {
    mostrarCi(await api("GET", "/api/calidad/ci"));
    estado.textContent = "";
  } catch (error) {
    estado.className = "estado error";
    estado.textContent = error.message;
  }
  boton.disabled = false;
}

el("btn-ci").addEventListener("click", actualizarCi);
void actualizarCi(); // se consulta sola; es independiente de SonarQube
