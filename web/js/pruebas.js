/* Ventana 3: ejecuta la suite de pruebas y muestra el resultado. */
let datos = null;

const ETIQUETA = {
  ok: ["ok", "aprobada"],
  falló: ["mal", "falló"],
  error: ["mal", "error"],
  omitida: ["", "omitida"],
};

/** Cuenta los casos de un tipo por resultado. */
function resumenTipo(tipo, pruebas) {
  const casos = pruebas.filter((p) => p.tipo === tipo);
  const cuenta = (r) => casos.filter((p) => p.resultado === r).length;
  return {
    tipo,
    total: casos.length,
    aprobadas: cuenta("ok"),
    noAprobadas: cuenta("falló") + cuenta("error"),
    omitidas: cuenta("omitida"),
  };
}

/** Interpreta la tabla por tipo a partir de los recuentos recibidos. */
function analizarTipos(grupos) {
  if (!grupos.length) return "";
  const total = grupos.reduce((a, g) => a + g.total, 0);
  const malas = grupos.reduce((a, g) => a + g.noAprobadas, 0);
  const omitidas = grupos.reduce((a, g) => a + g.omitidas, 0);
  const ejecutadas = total - omitidas;
  const frases = [];

  if (!ejecutadas) {
    frases.push(`Los ${pluralizar(total, "caso", "casos")} de la última ejecución quedaron omitidos, así que no verifican nada.`);
  } else if (!malas) {
    frases.push(
      `No hubo fallos ni errores: ${ejecutadas === total ? "aprobaron los" : "aprobaron los " + ejecutadas + " casos ejecutados de"} ${pluralizar(total, "caso", "casos")} en ${pluralizar(grupos.length, "tipo", "tipos")}.`,
    );
  } else {
    const conFallas = grupos.filter((g) => g.noAprobadas);
    const detalle = conFallas.map((g) => `${g.tipo} (${g.noAprobadas} de ${g.total})`).join(", ");
    frases.push(`${pluralizar(malas, "caso no aprobó", "casos no aprobaron")} de ${ejecutadas} ejecutados, en: ${detalle}.`);
    const limpios = grupos.filter((g) => !g.noAprobadas).map((g) => g.tipo);
    if (limpios.length) frases.push(`Sin fallos en: ${limpios.join(", ")}.`);
  }
  if (omitidas && ejecutadas) {
    frases.push(`${pluralizar(omitidas, "caso omitido no aporta", "casos omitidos no aportan")} verificación.`);
  }

  if (grupos.length > 1) {
    const orden = [...grupos].sort((a, b) => b.total - a.total);
    const parecidos = orden.filter((g) => casiIguales(g.total, orden[0].total));
    frases.push(
      parecidos.length > 1
        ? `${parecidos.map((g) => g.tipo).join(" y ")} tienen una cantidad de casos similar (${orden[0].total} como máximo).`
        : `${orden[0].tipo} concentra ${porcentajeDe(orden[0].total, total)} de los casos.`,
    );
  }
  frases.push("La tabla cuenta casos, no líneas cubiertas: aprobar indica que lo comprobado se cumple, no que todo esté comprobado.");
  return frases.join(" ");
}

/** Interpreta los casos visibles: resultados y distribución del tiempo. */
function analizarDetalle(filas, soloFallas) {
  if (!filas.length) {
    return soloFallas ? "Ningún caso de la selección quedó sin aprobar." : "";
  }
  const cuenta = (r) => filas.filter((p) => p.resultado === r).length;
  const malas = cuenta("falló") + cuenta("error");
  const omitidas = cuenta("omitida");
  const frases = [
    `Se muestran ${pluralizar(filas.length, "caso", "casos")}: ${pluralizar(cuenta("ok"), "aprobado", "aprobados")}, ${pluralizar(malas, "no aprobado", "no aprobados")} y ${pluralizar(omitidas, "omitido", "omitidos")}.`,
  ];
  const conProblema = filas.filter((p) => p.resultado === "falló" || p.resultado === "error");
  if (conProblema.length) {
    const nombres = conProblema.slice(0, 3).map((p) => `${p.nombre} (${p.grupo})`).join("; ");
    frases.push(`No aprobados: ${nombres}${conProblema.length > 3 ? ` y ${conProblema.length - 3} más` : ""}.`);
  }

  const lentas = [...filas].sort((a, b) => b.segundos - a.segundos);
  const suma = filas.reduce((a, p) => a + p.segundos, 0);
  if (suma <= 0) {
    frases.push("Los tiempos informados son 0 s, por debajo de la resolución del informe: no permiten comparar casos.");
  } else if (filas.length > 1) {
    const [primera, segunda] = lentas;
    const tres = lentas.slice(0, 3).reduce((a, p) => a + p.segundos, 0);
    if (casiIguales(primera.segundos, segunda.segundos)) {
      frases.push(`Los dos casos más lentos tardaron lo mismo dentro de la tolerancia (${fmt(primera.segundos, 3)} s y ${fmt(segunda.segundos, 3)} s), por lo que no se destaca ninguno.`);
    } else {
      frases.push(`El más lento fue ${primera.nombre} (${fmt(primera.segundos, 3)} s, ${porcentajeDe(primera.segundos, suma)} del tiempo sumado).`);
    }
    frases.push(
      filas.length > 3 && tres / suma >= 0.5
        ? `Los tres casos más lentos suman ${porcentajeDe(tres, suma)} del tiempo: está concentrado en pocos casos.`
        : "El tiempo está repartido entre los casos, sin que unos pocos dominen.",
    );
    frases.push(`Suma de tiempos de los casos mostrados: ${fmt(suma, 2)} s; depende de la máquina y no equivale al tiempo total de pytest.`);
  }
  return frases.join(" ");
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
  const tablaTipos = el("tabla-tipos").querySelector("tbody");
  const grupos = tipos.map((t) => resumenTipo(t, datos.pruebas));
  if (!tipos.length) {
    tablaTipos.innerHTML = '<tr><td colspan="5">La última ejecución no devolvió casos de prueba.</td></tr>';
  } else llenarTabla(
    tablaTipos,
    grupos.map((g) => [
      g.tipo,
      { t: g.total, n: true },
      { t: g.aprobadas, n: true },
      { t: g.noAprobadas, n: true },
      { t: g.omitidas, n: true },
    ]),
  );
  el("analisis-tipos").textContent = analizarTipos(grupos);

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
  const tablaDetalle = el("tabla-pruebas").querySelector("tbody");
  el("analisis-detalle").textContent = analizarDetalle(filas, soloFallas);
  if (!filas.length) {
    tablaDetalle.innerHTML = '<tr><td colspan="5">No hay casos que coincidan con los filtros.</td></tr>';
    return;
  }
  llenarTabla(
    tablaDetalle,
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
    guardarResultado("pruebas", datos);
    estado.textContent = "Ejecución completada ahora.";
    mostrar();
  } catch (error) {
    estado.className = "estado error";
    estado.textContent =
      error.message + " Los datos visibles, si los hay, corresponden a la última ejecución guardada.";
  }
  boton.disabled = false;
}

const pruebasGuardadas = leerResultado("pruebas");
if (pruebasGuardadas?.datos) {
  datos = pruebasGuardadas.datos;
  mostrar();
  el("estado-pruebas").textContent = etiquetaResultadoGuardado(pruebasGuardadas);
}

el("btn-pruebas").addEventListener("click", ejecutar);
el("filtro-tipo").addEventListener("change", () => datos && detalle());
el("solo-fallas").addEventListener("change", () => datos && detalle());
// La suite se ejecuta únicamente cuando la persona lo solicita.
