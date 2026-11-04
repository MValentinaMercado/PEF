/* Utilidades compartidas por todas las ventanas. */
const el = (id) => document.getElementById(id);
// Identidad de cada algoritmo en gráficos: gris cálido, naranja y naranja oscuro.
const COLORES = { BFS: "#9a948c", Dijkstra: "#f28c28", "A*": "#b8501a" };

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

/** Conserva resultados de experimentos en esta pestaña sin volver a ejecutarlos. */
function guardarResultado(clave, datos) {
  try {
    sessionStorage.setItem(
      `resultado:${clave}`,
      JSON.stringify({ datos, guardado: new Date().toISOString() }),
    );
  } catch (_) {
    // La interfaz sigue funcionando aunque el navegador bloquee el almacenamiento.
  }
}

/** Recupera una medición anterior y su fecha; nunca la presenta como actual. */
function leerResultado(clave) {
  try {
    const texto = sessionStorage.getItem(`resultado:${clave}`);
    return texto ? JSON.parse(texto) : null;
  } catch (_) {
    return null;
  }
}

function etiquetaResultadoGuardado(resultado) {
  if (!resultado?.guardado) return "";
  const fecha = new Date(resultado.guardado);
  return Number.isNaN(fecha.getTime())
    ? "Resultado guardado en esta pestaña."
    : `Último resultado de esta pestaña: ${fecha.toLocaleString("es-AR")}.`;
}

/** Diferencia relativa máxima para considerar dos valores prácticamente iguales. */
const TOLERANCIA_IGUALES = 0.05;

/** Indica si dos magnitudes difieren menos que la tolerancia común. */
function casiIguales(a, b, tolerancia = TOLERANCIA_IGUALES) {
  const mayor = Math.max(Math.abs(a), Math.abs(b));
  return mayor === 0 || Math.abs(a - b) / mayor <= tolerancia;
}

/** "1 caso" / "3 casos". */
const pluralizar = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

/** Parte sobre el total como porcentaje entero: "40 %". */
const porcentajeDe = (parte, total) => `${fmt((parte / total) * 100, 0)} %`;

/** Recuento por clave, de mayor a menor: [[clave, cantidad], ...]. */
function contarPor(filas, clave, peso = () => 1) {
  const cuenta = new Map();
  for (const f of filas) cuenta.set(clave(f), (cuenta.get(clave(f)) || 0) + peso(f));
  return [...cuenta].sort((a, b) => b[1] - a[1]);
}

/** Mediana de una lista de números (lista no vacía). */
function mediana(valores) {
  const orden = [...valores].sort((a, b) => a - b);
  const medio = Math.floor(orden.length / 2);
  return orden.length % 2 ? orden[medio] : (orden[medio - 1] + orden[medio]) / 2;
}

/** "A", "A y B", "A, B y C". */
function listar(nombres) {
  if (nombres.length < 2) return nombres.join("");
  return `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
}

/** Filas con el menor valor (o casi igual a él, con la tolerancia común). */
function conMenor(filas, valor, tolerante = true) {
  const minimo = Math.min(...filas.map(valor));
  const cerca = (f) =>
    tolerante ? casiIguales(valor(f), minimo) : valor(f) === minimo;
  return { minimo, filas: filas.filter(cerca) };
}

/** Compara una magnitud entre filas: similar en todas, o cuáles usan menos. */
function compararMagnitud(filas, valor, nombre, formato, nombreDe = (f) => f.algoritmo) {
  const { minimo, filas: menores } = conMenor(filas, valor);
  const maximo = Math.max(...filas.map(valor));
  if (menores.length === filas.length) {
    return `${nombre}: similar en todos (${formato(maximo)} como máximo).`;
  }
  const nombres = menores.map(nombreDe);
  return `${nombre}: ${listar(nombres)} ${nombres.length > 1 ? "registran" : "registra"} menos (${formato(minimo)} frente a ${formato(maximo)}).`;
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

/** Ficha de resultado: un valor destacado y su título (clase: ok o mal). */
function ficha(titulo, valor, clase = "") {
  return (
    `<div class="ficha"><b class="${clase}">${esc(valor)}</b>` +
    `${esc(titulo)}</div>`
  );
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
    copiarTexto(texto)
      .then(() => {
        copiar.textContent = "Copiado";
        setTimeout(() => (copiar.textContent = "Copiar"), 1200);
      })
      .catch(() => {
        copiar.textContent = "No se pudo copiar";
        setTimeout(() => (copiar.textContent = "Copiar"), 1800);
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
