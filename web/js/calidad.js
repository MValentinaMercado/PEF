/* Ventana 5: estado del proyecto en SonarQube Cloud. */
const el = (id) => document.getElementById(id);

function ficha(titulo, valor, clase = "") {
  return (
    `<div class="ficha"><b class="${clase}">${esc(valor)}</b>` +
    `${esc(titulo)}</div>`
  );
}

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
