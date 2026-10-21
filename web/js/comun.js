/* Utilidades compartidas por todas las ventanas. */
const COLORES = { BFS: "#e8b04a", Dijkstra: "#4cc38a", "A*": "#ef6f6c" };

/** Llama a la API y devuelve el JSON; lanza Error con el detalle. */
async function api(metodo, url, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }
  const respuesta = await fetch(url, opciones);
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const detalle = datos.detail;
    throw new Error(
      Array.isArray(detalle)
        ? detalle.map((d) => d.msg).join("; ")
        : detalle || respuesta.statusText,
    );
  }
  return datos;
}

/** Escapa texto para insertarlo en HTML. */
function esc(texto) {
  return String(texto).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}

/** Rellena un <tbody>; celdas {t: texto, n: numérica} o {h: HTML propio}. */
function llenarTabla(tbody, filas) {
  tbody.innerHTML = filas
    .map(
      (fila) =>
        "<tr>" +
        fila
          .map((c) => {
            const celda = typeof c === "object" ? c : { t: c };
            const contenido = celda.h !== undefined ? celda.h : esc(celda.t);
            return `<td class="${celda.n ? "num" : ""}">${contenido}</td>`;
          })
          .join("") +
        "</tr>",
    )
    .join("");
}

/** Formatea un número con separador de miles al estilo es-AR. */
const fmt = (n, dec = 2) =>
  Number(n).toLocaleString("es-AR", {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  });

/* ---------- Comandos de consola de cada tabla o resultado ----------
 * Cualquier elemento con data-api y/o data-cmd recibe un botón "</>" que
 * muestra, al pasar el cursor o al hacer clic, el endpoint y los comandos
 * que producen esos mismos datos.
 *   data-api  "MÉTODO /ruta" (varios separados con "|")
 *   data-body cuerpo JSON de la petición (opcional)
 *   data-cmd  comandos locales (varios separados con "|")
 */
function comandoCurl(endpoint, cuerpo) {
  const [metodo, ruta] = endpoint.trim().split(/\s+/);
  let cmd = `curl -X ${metodo} ${location.origin}${ruta}`;
  if (cuerpo) {
    cmd +=
      ` -H "Content-Type: application/json"` +
      ` -d "${cuerpo.replace(/"/g, '\\"')}"`;
  }
  return cmd;
}

function copiarTexto(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(texto);
  }
  const area = document.createElement("textarea");
  area.value = texto;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
  return Promise.resolve();
}

function filaComando(etiqueta, texto) {
  const fila = document.createElement("div");
  fila.className = "cmd-fila";
  const rotulo = document.createElement("span");
  rotulo.className = "cmd-rotulo";
  rotulo.textContent = etiqueta;
  const codigo = document.createElement("code");
  codigo.textContent = texto;
  const copiar = document.createElement("button");
  copiar.type = "button";
  copiar.className = "cmd-copiar";
  copiar.textContent = "Copiar";
  copiar.addEventListener("click", (evento) => {
    evento.stopPropagation();
    copiarTexto(texto).then(() => {
      copiar.textContent = "Copiado";
      setTimeout(() => (copiar.textContent = "Copiar"), 1200);
    });
  });
  fila.append(rotulo, codigo, copiar);
  return fila;
}

function agregarComandos(elemento) {
  const endpoints = (elemento.dataset.api || "").split("|").filter(Boolean);
  const locales = (elemento.dataset.cmd || "").split("|").filter(Boolean);
  const cuerpo = elemento.dataset.body || "";
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "cmd";
  boton.textContent = "</>";
  boton.setAttribute("aria-label", "Ver endpoint y comando de consola");
  const caja = document.createElement("div");
  caja.className = "cmd-tip";
  caja.setAttribute("role", "tooltip");
  endpoints.forEach((e) => {
    caja.appendChild(
      filaComando("Endpoint", e.trim().replace(" ", " " + location.origin)),
    );
    caja.appendChild(filaComando("Consola", comandoCurl(e, cuerpo)));
  });
  locales.forEach((c) => caja.appendChild(filaComando("Terminal", c.trim())));
  document.body.appendChild(caja);
  elemento.appendChild(boton);

  let temporizador = null;
  const mostrar = () => {
    clearTimeout(temporizador);
    document.querySelectorAll(".cmd-tip.visible").forEach((t) => {
      if (t !== caja) t.classList.remove("visible");
    });
    caja.classList.add("visible");
    const r = boton.getBoundingClientRect();
    const izquierda = Math.min(
      Math.max(8, r.left),
      Math.max(8, window.innerWidth - caja.offsetWidth - 8),
    );
    caja.style.left = izquierda + "px";
    caja.style.top = r.bottom + 6 + "px";
  };
  const ocultar = () => {
    temporizador = setTimeout(() => {
      if (!caja.dataset.fijo) caja.classList.remove("visible");
    }, 150);
  };
  boton.addEventListener("mouseenter", mostrar);
  boton.addEventListener("mouseleave", ocultar);
  boton.addEventListener("focus", mostrar);
  boton.addEventListener("blur", ocultar);
  caja.addEventListener("mouseenter", () => clearTimeout(temporizador));
  caja.addEventListener("mouseleave", ocultar);
  boton.addEventListener("click", () => {
    if (caja.dataset.fijo) {
      delete caja.dataset.fijo;
      caja.classList.remove("visible");
    } else {
      caja.dataset.fijo = "1";
      mostrar();
    }
  });
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") {
      delete caja.dataset.fijo;
      caja.classList.remove("visible");
    }
  });
  document.addEventListener("click", (evento) => {
    if (!caja.contains(evento.target) && evento.target !== boton) {
      delete caja.dataset.fijo;
      caja.classList.remove("visible");
    }
  });
  window.addEventListener(
    "scroll",
    () => {
      delete caja.dataset.fijo;
      caja.classList.remove("visible");
    },
    { passive: true },
  );
}

document.querySelectorAll("[data-api], [data-cmd]").forEach(agregarComandos);
