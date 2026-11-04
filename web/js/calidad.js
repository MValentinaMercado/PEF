/* Ventana Calidad: estado del proyecto en SonarQube Cloud y en GitHub Actions. */

/* ---------- Interpretación automática de las condiciones ---------- */

const numeroDe = (texto) => Number(/-?\d+(?:\.\d+)?/.exec(String(texto))?.[0]);

function analizarCondiciones(datos) {
  const condiciones = datos.condiciones;
  if (!condiciones.length) return "";
  const falla = condiciones.filter((c) => !c.ok);
  const frases = [
    `${pluralizar(condiciones.length, "condición", "condiciones")}: ${condiciones.length - falla.length} ${condiciones.length - falla.length === 1 ? "cumple" : "cumplen"} y ${falla.length} no.`,
  ];
  if (falla.length) {
    frases.push(
      "No cumplen: " + falla.map((c) => `${c.nombre} (valor ${c.valor}, se exige ${c.exigencia})`).join("; ") + ".",
    );
  } else if (datos.estado !== "OK") {
    frases.push(`Todas las condiciones listadas cumplen, pero SonarQube informa el estado general ${datos.estado}.`);
  }
  // Un cumplimiento "justo" depende del umbral: un umbral 0 (p. ej. "≤ 0") no tiene margen que medir.
  const justas = condiciones.filter((c) => {
    const umbral = numeroDe(c.exigencia);
    return c.ok && umbral !== 0 && casiIguales(numeroDe(c.valor), umbral);
  });
  if (justas.length) {
    frases.push(
      "Cumplen con poco margen (dentro de la tolerancia del umbral): " +
        justas.map((c) => `${c.nombre} (${c.valor} frente a ${c.exigencia})`).join("; ") + ".",
    );
  }
  if (condiciones.every((c) => c.nombre.endsWith("en código nuevo"))) {
    frases.push("Las condiciones miden el código nuevo, no todo el proyecto; las métricas de abajo describen el proyecto completo.");
  }
  return frases.join(" ");
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
  const condiciones = el("tabla-condiciones").querySelector("tbody");
  if (!datos.condiciones.length) {
    condiciones.innerHTML = '<tr><td colspan="4">SonarQube no devolvió condiciones para este análisis.</td></tr>';
  } else llenarTabla(
    condiciones,
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
  el("analisis-condiciones").textContent = analizarCondiciones(datos);
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
    const datos = await api("GET", "/api/calidad/sonar");
    mostrar(datos);
    guardarResultado("calidad:sonar", datos);
    estado.textContent = `Datos consultados: ${new Date().toLocaleString("es-AR")}.`;
  } catch (error) {
    estado.className = "estado error";
    estado.textContent =
      error.message + " Los datos visibles, si los hay, corresponden a la última consulta guardada.";
  }
  boton.disabled = false;
}

const sonarGuardado = leerResultado("calidad:sonar");
if (sonarGuardado?.datos) {
  mostrar(sonarGuardado.datos);
  el("estado-calidad").textContent = etiquetaResultadoGuardado(sonarGuardado);
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

function fechaLegible(valor) {
  if (!valor) return "Fecha no informada por GitHub";
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime())
    ? "Fecha no disponible"
    : fecha.toLocaleString("es-AR");
}

/* ---------- Interpretación automática de etapas e historial ---------- */

function analizarEtapas(datos) {
  const etapas = datos.etapas;
  if (!etapas.length) return "";
  const estados = contarPor(etapas, (e) => e.estado);
  const frases = [
    `${pluralizar(etapas.length, "etapa", "etapas")}: ${estados.map(([e, n]) => `${e} ${n}`).join(", ")}.`,
  ];
  const sinAprobar = etapas.filter((e) => e.estado !== "aprobado" && e.estado !== "omitido");
  if (sinAprobar.length) {
    frases.push(
      "Sin aprobar: " + sinAprobar.map((e) => `${e.nombre} (${e.estado}${e.paso_fallido ? `, control «${e.paso_fallido}»` : ""})`).join("; ") + ".",
    );
  }
  if (etapas.some((e) => e.estado === "omitido")) {
    frases.push("Una etapa omitida no se ejecutó, por lo que no cuenta como aprobada.");
  }
  const controles = etapas.flatMap((e) => e.controles || []);
  if (controles.length) {
    const cuenta = (estado) => controles.filter((c) => c.estado === estado).length;
    frases.push(`Controles informados: ${controles.length} (${cuenta("aprobado")} aprobados, ${cuenta("rechazado")} rechazados, ${cuenta("omitido")} omitidos).`);
  }
  if (datos.ultima.estado === "en curso") {
    frases.push("La corrida sigue en curso: estados y tiempos pueden cambiar.");
    return frases.join(" ");
  }
  const medidas = etapas.filter((e) => e.segundos !== null && e.segundos !== undefined);
  const suma = medidas.reduce((a, e) => a + e.segundos, 0);
  if (medidas.length > 1 && suma > 0) {
    const [primera, segunda] = [...medidas].sort((a, b) => b.segundos - a.segundos);
    frases.push(
      casiIguales(primera.segundos, segunda.segundos)
        ? `Las dos etapas más largas (${primera.nombre} y ${segunda.nombre}) duraron prácticamente lo mismo: ninguna destaca.`
        : `La etapa más larga fue ${primera.nombre} (${duracion(primera.segundos)}, ${porcentajeDe(primera.segundos, suma)} de la suma de etapas).`,
    );
    const total = datos.ultima.segundos;
    if (total !== null && total !== undefined) {
      frases.push(
        casiIguales(suma, total)
          ? `La suma de las etapas (${duracion(suma)}) coincide con la duración de la corrida (${duracion(total)}): se ejecutaron prácticamente en secuencia.`
          : suma > total
            ? `La suma de las etapas (${duracion(suma)}) supera la duración de la corrida (${duracion(total)}): hubo etapas en paralelo.`
            : `La suma de las etapas (${duracion(suma)}) es menor que la duración de la corrida (${duracion(total)}); GitHub no atribuye la diferencia a ninguna etapa.`,
      );
    }
  }
  return frases.join(" ");
}

function analizarHistorial(datos) {
  const historial = datos.historial;
  if (!historial.length) return "";
  const frases = [];
  if (historial.length > 1) {
    const corte = historial.findIndex((c) => c.estado !== historial[0].estado);
    const racha = corte === -1 ? historial.length : corte;
    frases.push(
      racha > 1
        ? `Las ${racha} corridas más recientes tienen el mismo estado (${historial[0].estado}).`
        : `La más reciente (${historial[0].estado}) cambia el estado de la anterior (${historial[1].estado}).`,
    );
  }
  const terminadas = historial.filter((c) => c.estado !== "en curso" && c.segundos !== null && c.segundos !== undefined);
  if (terminadas.length > 1) {
    const tiempos = terminadas.map((c) => c.segundos);
    frases.push(`Duraciones entre ${duracion(Math.min(...tiempos))} y ${duracion(Math.max(...tiempos))} (mediana ${duracion(mediana(tiempos))}).`);
    const previas = terminadas.filter((c) => c !== historial[0]).map((c) => c.segundos);
    if (terminadas[0] === historial[0] && previas.length > 1) {
      const ref = mediana(previas);
      frases.push(
        casiIguales(historial[0].segundos, ref)
          ? "La más reciente está en línea con la mediana de las anteriores."
          : `La más reciente duró ${duracion(historial[0].segundos)}, ${historial[0].segundos > ref ? "más" : "menos"} que la mediana de las anteriores (${duracion(ref)}).`,
      );
    }
    if (new Set(terminadas.map((c) => c.estado)).size > 1) {
      frases.push("Una corrida rechazada puede cortarse antes: comparar duraciones entre estados distintos no es equivalente.");
    }
  }
  const eventos = contarPor(historial, (c) => c.evento || "evento no informado");
  if (eventos.length > 1) {
    frases.push(`Eventos que las dispararon: ${eventos.map(([e, n]) => `${e} (${n})`).join(", ")}.`);
  }
  return frases.join(" ");
}

function mostrarCi(datos) {
  const ultima = datos.ultima;
  el("veredicto-ci").innerHTML = ficha(
    `Última corrida · #${ultima.numero}`,
    ultima.estado.toUpperCase(),
    CLASE_ESTADO[ultima.estado] || "",
  );
  el("fecha-ci").textContent = `Iniciada: ${fechaLegible(ultima.inicio)}.`;
  el("conclusion-ci").textContent = datos.conclusion;
  const enlace = el("enlace-ci");
  enlace.href = datos.panel;
  enlace.hidden = false;

  const etapas = el("tabla-etapas").querySelector("tbody");
  if (!datos.etapas.length) {
    etapas.innerHTML = '<tr><td colspan="5">GitHub todavía no informa etapas para esta corrida.</td></tr>';
  } else {
    llenarTabla(
      etapas,
      datos.etapas.map((e) => {
        const controles = (e.controles || []).map((c) =>
          `<li>${esc(c.nombre)}: ${estadoHtml(c.estado)}</li>`,
        ).join("");
        return [
          e.nombre,
          { h: estadoHtml(e.estado) },
          duracion(e.segundos),
          e.paso_fallido || "—",
          {
            h: `${controles ? `<details><summary>${(e.controles || []).length} controles</summary><ul>${controles}</ul></details>` : "—"}` +
              (e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">Abrir registro</a>` : ""),
          },
        ];
      }),
    );
  }

  el("analisis-etapas").textContent = analizarEtapas(datos);
  el("analisis-historial").textContent = analizarHistorial(datos);
  const historial = el("tabla-historial").querySelector("tbody");
  if (!datos.historial.length) {
    historial.innerHTML = '<tr><td colspan="5">No hay corridas anteriores disponibles.</td></tr>';
  } else {
    llenarTabla(
      historial,
      datos.historial.map((c) => [
        { h: enlaceHtml(c.url, `#${c.numero}`) },
        fechaLegible(c.inicio),
        { h: estadoHtml(c.estado) },
        {
          h: `<strong>${esc(c.titulo || "Sin título informado")}</strong><br><code>${esc(c.commit)}</code><small> · ${esc(c.evento || "evento no informado")}</small>`,
        },
        duracion(c.segundos),
      ]),
    );
  }
  const cantidad = datos.historial.length;
  el("contexto-historial").textContent =
    `Se muestran hasta ${cantidad} corridas recientes de la rama ${datos.rama}. ` +
    "El historial es orientativo; el detalle completo está en GitHub Actions.";
}

async function actualizarCi() {
  const boton = el("btn-ci"),
    estado = el("estado-ci");
  boton.disabled = true;
  estado.className = "estado";
  estado.textContent = "Consultando GitHub Actions…";
  try {
    const datos = await api("GET", "/api/calidad/ci");
    mostrarCi(datos);
    guardarResultado("calidad:ci", datos);
    estado.textContent = `Datos consultados: ${new Date().toLocaleString("es-AR")}.`;
  } catch (error) {
    estado.className = "estado error";
    estado.textContent = error.message;
    el("fecha-ci").textContent =
      "No se pudo actualizar. Los datos visibles, si los hay, corresponden a la consulta anterior.";
  }
  boton.disabled = false;
}

const ciGuardado = leerResultado("calidad:ci");
if (ciGuardado?.datos) {
  mostrarCi(ciGuardado.datos);
  el("estado-ci").textContent = etiquetaResultadoGuardado(ciGuardado);
}
el("btn-ci").addEventListener("click", actualizarCi);
void actualizarCi(); // se consulta sola; es independiente de SonarQube
