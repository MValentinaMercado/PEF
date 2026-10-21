/* Ventana 2: ejecuta las mediciones reales y las muestra. */
const el = (id) => document.getElementById(id);
const MIL = (n) => Number(n).toLocaleString("es-AR");
const GRAFICOS = [
  ["tiempo_ms", "Tiempo medio (ms)"],
  ["memoria_kb", "Memoria pico (KB)"],
  ["nodos_explorados", "Nodos explorados"],
];

/** Conecta un botón con un endpoint y una función que muestra el resultado. */
function enlazar(nombre, mostrar) {
  const boton = el("btn-" + nombre),
    estado = el("estado-" + nombre);
  const ejecutar = async () => {
    boton.disabled = true;
    estado.className = "estado";
    estado.textContent = "Ejecutando…";
    const inicio = performance.now();
    try {
      mostrar(await api("POST", "/api/analisis/" + nombre));
      estado.textContent =
        "Listo en " + fmt((performance.now() - inicio) / 1000, 1) + " s.";
    } catch (error) {
      estado.className = "estado error";
      estado.textContent = error.message;
    }
    boton.disabled = false;
  };
  boton.addEventListener("click", ejecutar);
  return ejecutar;
}

/** Gráfico SVG sencillo para comparar una métrica entre algoritmos en un tamaño. */
function graficoGrupo(titulo, atributo, filas) {
  const W = 560,
    H = 230,
    left = 54,
    right = 18,
    top = 28,
    bottom = 48;
  const max = Math.max(...filas.map((f) => Number(f[atributo]) || 0), 0.0001);
  const colores = {
    BFS: COLORES.BFS,
    Dijkstra: COLORES.Dijkstra,
    "A*": COLORES["A*"],
  };
  const plotH = H - top - bottom,
    plotW = W - left - right;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${titulo}"><text x="${W / 2}" y="16" text-anchor="middle" font-size="13" font-weight="bold" fill="currentColor">${titulo}</text>`;
  for (let i = 0; i <= 4; i++) {
    const y = top + (plotH * i) / 4,
      v = max * (1 - i / 4);
    svg += `<line x1="${left}" x2="${W - right}" y1="${y}" y2="${y}" stroke="currentColor" opacity=".15"/><text x="${left - 7}" y="${y + 4}" text-anchor="end" font-size="10" fill="currentColor">${fmt(v, 3)}</text>`;
  }
  const step = plotW / Math.max(filas.length, 1),
    bw = Math.min(90, step * 0.55);
  filas.forEach((f, i) => {
    const v = Math.max(0, Number(f[atributo]) || 0),
      h = (plotH * v) / max,
      x = left + i * step + (step - bw) / 2,
      y = top + plotH - h;
    svg += `<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(h, 1)}" fill="${colores[f.algoritmo] || "#64748b"}"><title>${f.algoritmo}: ${fmt(v, 4)}</title></rect><text x="${x + bw / 2}" y="${H - bottom + 17}" text-anchor="middle" font-size="11" fill="currentColor">${f.algoritmo}</text>`;
  });
  return svg + "</svg>";
}

function tarjetaBenchmark(nodos, filas) {
  const id = `benchmark-${nodos}`;
  const tr = filas
    .map(
      (f) =>
        `<tr><td>${esc(f.algoritmo)}</td><td>${fmt(f.tiempo_ms, 4)}</td><td>${fmt(f.memoria_kb, 1)}</td><td>${MIL(Math.round(f.nodos_explorados))}</td></tr>`,
    )
    .join("");
  const graficos = [
    ["tiempo_ms", "Tiempo medio (ms)"],
    ["memoria_kb", "Memoria pico (KB)"],
    ["nodos_explorados", "Nodos explorados"],
  ]
    .map(
      ([campo, titulo]) =>
        `<div class="grafico-grupo">${graficoGrupo(titulo, campo, filas)}</div>`,
    )
    .join("");
  const salida = filas
    .map(
      (f) =>
        `${f.algoritmo}: ${fmt(f.tiempo_ms, 4)} ms; ${fmt(f.memoria_kb, 1)} KB; ${Math.round(f.nodos_explorados)} nodos explorados.`,
    )
    .join("\n");
  return `<article class="grupo-resultado"><h3>${MIL(nodos)} nodos</h3><div class="tabla-scroll"><table><thead><tr><th>Algoritmo</th><th>Tiempo medio (ms)</th><th>Memoria pico (KB)</th><th>Nodos explorados</th></tr></thead><tbody>${tr}</tbody></table></div><div class="graficos-grupo">${graficos}</div><pre class="salida-consola">${esc(salida)}</pre></article>`;
}

const ejecutarBenchmark = enlazar("benchmark", (filas) => {
  const grupos = [...new Set(filas.map((f) => f.nodos))].sort((a, b) => a - b);
  el("resultados-benchmark").innerHTML = grupos
    .map((n) =>
      tarjetaBenchmark(
        n,
        filas.filter((f) => f.nodos === n),
      ),
    )
    .join("");
});

const ejecutarCache = enlazar("cache", (r) => {
  llenarTabla(el("tabla-cache").querySelector("tbody"), [
    [
      "Sin caché",
      { t: fmt(r.sin_cache[0]), n: true },
      { t: fmt(r.sin_cache[1], 1), n: true },
      { t: r.total_consultas, n: true },
      "—",
      "—",
    ],
    [
      "Con caché",
      { t: fmt(r.con_cache[0]), n: true },
      { t: fmt(r.con_cache[1], 1), n: true },
      { t: r.total_consultas, n: true },
      { t: r.aciertos, n: true },
      { t: r.fallos, n: true },
    ],
  ]);
  const tras = r.fallo_tras_cambio ? "fallo" : "acierto (¡error!)";
  const repetir = r.acierto_al_repetir ? "acierto" : "fallo";
  el("texto-cache").textContent =
    `Se calcularon solo ${r.fallos} rutas; las otras ${r.aciertos} salieron ` +
    `de la caché (cálculos repetidos evitados). Al modificar el grafo, la ` +
    `misma consulta fue un ${tras} (invalidaciones: ${r.invalidaciones}) y ` +
    `al repetirla fue un ${repetir}.`;
});

const ejecutarConcurrencia = enlazar("concurrencia", (filas) => {
  llenarTabla(
    el("tabla-concurrencia").querySelector("tbody"),
    filas.map((f) => [
      f.modo,
      { t: fmt(f.tiempo_ms), n: true },
      { t: fmt(f.memoria_kb, 1), n: true },
      { t: f.consultas_procesadas, n: true },
      { t: fmt(f.aceleracion) + "×", n: true },
    ]),
  );
});

const ejecutarEntradaSalida = enlazar("entrada_salida", (r) => {
  const medida = (f) => [
    f.modo,
    { t: fmt(f.tiempo_ms), n: true },
    { t: fmt(f.memoria_kb, 1), n: true },
    { t: MIL(f.lineas), n: true },
    { t: fmt(f.aceleracion) + "×", n: true },
  ];
  const cuerpo = (id) => el(id).querySelector("tbody");
  llenarTabla(cuerpo("tabla-escritura"), r.escritura.map(medida));
  llenarTabla(cuerpo("tabla-lectura"), r.lectura.map(medida));
  llenarTabla(
    cuerpo("tabla-paralelo"),
    r.paralelo.map((f) => [
      f.modo,
      { t: fmt(f.tiempo_ms), n: true },
      { t: MIL(f.lotes), n: true },
      { t: MIL(f.lineas), n: true },
      { t: fmt(f.aceleracion) + "×", n: true },
    ]),
  );
  el("texto-entrada_salida").textContent =
    `Archivo de ${MIL(Math.round(r.tamano_kb))} KB con ${MIL(r.lineas)} líneas. ` +
    `Lotes de ${MIL(r.tamano_lote)} líneas al escribir y leer, y de ` +
    `${MIL(r.tamano_lote_paralelo)} en el procesamiento paralelo. ` +
    (r.resultados_coinciden
      ? "Todos los modos produjeron exactamente el mismo resultado."
      : "¡Atención: los modos no produjeron el mismo resultado!");
});

/** Pide a la API que levante SnakeViz y arma un botón por algoritmo. */
async function prepararSnakeviz(algoritmos) {
  const estado = el("estado-snakeviz"),
    selector = el("selector-snakeviz"),
    marco = el("marco-snakeviz"),
    enlace = el("enlace-snakeviz");
  estado.className = "estado";
  estado.textContent = "Iniciando SnakeViz…";
  try {
    const urls = await api("POST", "/api/analisis/snakeviz");
    // SnakeViz corre en otro puerto del mismo equipo que sirve la página.
    const direccion = (u) => u.replace("127.0.0.1", location.hostname);
    const mostrar = (nombre) => {
      marco.src = direccion(urls[nombre]);
      marco.hidden = false;
      enlace.href = direccion(urls[nombre]);
      enlace.hidden = false;
      selector.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("principal", b.dataset.algoritmo === nombre);
      });
    };
    selector.innerHTML = algoritmos
      .map(
        (n) =>
          `<button type="button" data-algoritmo="${esc(n)}">${esc(n)}</button>`,
      )
      .join("");
    selector
      .querySelectorAll("button")
      .forEach((b) =>
        b.addEventListener("click", () => mostrar(b.dataset.algoritmo)),
      );
    estado.textContent = "";
    mostrar(algoritmos[0]);
  } catch (error) {
    estado.className = "estado error";
    estado.textContent = error.message;
  }
}

const ejecutarPerfilado = enlazar("perfilado", ({ cpu, memoria }) => {
  prepararSnakeviz(Object.keys(cpu));
  const nombres = { BFS: "BFS", Dijkstra: "Dijkstra", "A*": "A*" };
  el("resultados-perfilado").innerHTML = Object.entries(cpu)
    .map(([algoritmo, funciones]) => {
      const maximo = Math.max(...funciones.map((f) => f.tiempo_propio), 1e-12);
      const filas = funciones
        .map((f) => {
          const ancho = Math.round((100 * f.tiempo_propio) / maximo);
          return `<tr><td>${esc(f.funcion)}</td><td>${MIL(f.llamadas)}</td><td>${fmt(f.tiempo_propio, 6)}</td><td>${fmt(f.tiempo_acumulado, 6)}</td><td><div class="barra-t" style="width:${ancho}%;background:${COLORES[algoritmo] || "#64748b"}"></div></td></tr>`;
        })
        .join("");
      const salida =
        funciones
          .slice(0, 5)
          .map(
            (f) =>
              `${f.funcion}: ${f.llamadas} llamadas, ${fmt(f.tiempo_propio, 6)} s propios, ${fmt(f.tiempo_acumulado, 6)} s acumulados.`,
          )
          .join("\n") || "Sin funciones registradas.";
      return `<article class="grupo-resultado"><h3>${nombres[algoritmo] || esc(algoritmo)}</h3><div class="tabla-scroll"><table><thead><tr><th>Función</th><th>Llamadas</th><th>Tiempo propio (s)</th><th>Tiempo acumulado (s)</th><th>Peso relativo</th></tr></thead><tbody>${filas}</tbody></table></div><pre class="salida-consola">${esc(salida)}</pre></article>`;
    })
    .join("");
  llenarTabla(
    el("tabla-memoria").querySelector("tbody"),
    memoria.map((f) => [
      { t: f.linea, n: true },
      { t: fmt(f.memoria_mib, 1), n: true },
      { t: fmt(f.incremento_mib, 1), n: true },
      { h: `<code>${esc(f.codigo)}</code>` },
    ]),
  );
  el("salida-memoria").textContent =
    memoria
      .map(
        (f) =>
          `Línea ${f.linea}: ${fmt(f.memoria_mib, 1)} MiB (${fmt(f.incremento_mib, 1)} MiB) — ${f.codigo}`,
      )
      .join("\n") || "memory_profiler no devolvió líneas para mostrar.";
});

/** Gráfico SVG con ejes logarítmicos: tiempo observado (línea) y esperado (guiones). */
function graficoEscalabilidad(filas) {
  const W = 640,
    H = 320,
    izq = 62,
    der = 20,
    arriba = 20,
    abajo = 64;
  const nodos = [...new Set(filas.map((f) => f.nodos))];
  const valores = filas.flatMap((f) => [f.tiempo_ms, f.esperado_ms]);
  const x0 = Math.log10(Math.min(...nodos)),
    x1 = Math.log10(Math.max(...nodos));
  const y0 = Math.floor(Math.log10(Math.min(...valores))),
    y1 = Math.ceil(Math.log10(Math.max(...valores)));
  const X = (n) =>
    izq + ((Math.log10(n) - x0) / (x1 - x0 || 1)) * (W - izq - der);
  const Y = (v) =>
    arriba +
    (1 - (Math.log10(v) - y0) / (y1 - y0 || 1)) * (H - arriba - abajo);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Tiempo observado y esperado según la cantidad de nodos" style="max-width:${W}px;width:100%">`;
  for (let e = y0; e <= y1; e++) {
    const y = Y(10 ** e);
    svg += `<line x1="${izq}" x2="${W - der}" y1="${y}" y2="${y}" stroke="#64748b" stroke-opacity=".25"/><text x="${izq - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="currentColor">${MIL(10 ** e)}</text>`;
  }
  for (const n of nodos) {
    svg += `<text x="${X(n)}" y="${H - abajo + 16}" text-anchor="middle" font-size="11" fill="currentColor">${MIL(n)}</text>`;
  }
  svg += `<text x="${(izq + W - der) / 2}" y="${H - abajo + 34}" text-anchor="middle" font-size="12" fill="currentColor">Nodos (escala logarítmica)</text>`;
  svg += `<text x="14" y="${(arriba + H - abajo) / 2}" text-anchor="middle" font-size="12" fill="currentColor" transform="rotate(-90 14 ${(arriba + H - abajo) / 2})">Tiempo por consulta (ms, log)</text>`;
  let leyenda = 0;
  for (const algoritmo of Object.keys(COLORES)) {
    const propias = filas.filter((f) => f.algoritmo === algoritmo);
    const linea = (campo, guiones) =>
      `<polyline fill="none" stroke="${COLORES[algoritmo]}" stroke-width="2" ${guiones ? 'stroke-dasharray="5 4" stroke-opacity=".7"' : ""} points="${propias.map((f) => `${X(f.nodos)},${Y(f[campo])}`).join(" ")}"/>`;
    svg += linea("tiempo_ms", false) + linea("esperado_ms", true);
    svg += propias
      .map(
        (f) =>
          `<circle cx="${X(f.nodos)}" cy="${Y(f.tiempo_ms)}" r="3" fill="${COLORES[algoritmo]}"/>`,
      )
      .join("");
    const lx = izq + 10 + leyenda * 130;
    svg += `<line x1="${lx}" x2="${lx + 18}" y1="${H - 10}" y2="${H - 10}" stroke="${COLORES[algoritmo]}" stroke-width="2"/><text x="${lx + 24}" y="${H - 6}" font-size="11" fill="currentColor">${esc(algoritmo)}</text>`;
    leyenda++;
  }
  svg += `<text x="${W - der}" y="${H - 6}" text-anchor="end" font-size="11" fill="currentColor">línea: observado · guiones: esperado teórico</text></svg>`;
  return svg;
}

/** Separa el crecimiento del tiempo entre nodos explorados y costo por nodo. */
function descomposicion(filas, desde = 10000, hasta = 100000) {
  const factorLog = Math.log2(hasta) / Math.log2(desde);
  return ["BFS", "Dijkstra", "A*"].flatMap((algoritmo) => {
    const a = filas.find((f) => f.algoritmo === algoritmo && f.nodos === desde);
    const b = filas.find((f) => f.algoritmo === algoritmo && f.nodos === hasta);
    if (!a || !b) return [];
    const veces = (n) => ({ t: fmt(n, 2) + " ×", n: true });
    return [
      [
        algoritmo,
        veces(b.tiempo_ms / a.tiempo_ms),
        veces(b.nodos_explorados / a.nodos_explorados),
        veces(b.us_por_nodo / a.us_por_nodo),
        veces(algoritmo === "BFS" ? 1 : factorLog),
      ],
    ];
  });
}

const ejecutarEscalabilidad = enlazar("escalabilidad", ({ filas, grafos }) => {
  el("grafico-escalabilidad").innerHTML = graficoEscalabilidad(filas);
  llenarTabla(
    el("tabla-escalabilidad").querySelector("tbody"),
    filas.map((f) => [
      { t: MIL(f.nodos), n: true },
      { t: MIL(f.aristas), n: true },
      f.algoritmo,
      { t: fmt(f.tiempo_ms, 1), n: true },
      { t: fmt(f.esperado_ms, 1), n: true },
      { t: fmt(f.razon, 2), n: true },
      { t: MIL(Math.round(f.nodos_explorados)), n: true },
      { t: fmt(f.esperado_explorados_ms, 1), n: true },
      { t: fmt(f.razon_explorados, 2), n: true },
      { t: fmt(f.us_por_nodo, 2), n: true },
      { t: MIL(Math.round(f.memoria_kb)), n: true },
    ]),
  );
  llenarTabla(
    el("tabla-descomposicion").querySelector("tbody"),
    descomposicion(filas),
  );
  llenarTabla(
    el("tabla-grafos").querySelector("tbody"),
    grafos.map((g) => [
      { t: MIL(g.nodos), n: true },
      { t: MIL(g.aristas), n: true },
      { t: fmt(g.memoria_mb, 1), n: true },
      { t: MIL(Math.round((g.memoria_mb * 1024 * 1024) / g.nodos)), n: true },
      { t: fmt(g.segundos, 2), n: true },
    ]),
  );
});

const ejecutarLineas = enlazar("lineas", (algoritmos) => {
  el("resultados-lineas").innerHTML = Object.entries(algoritmos)
    .map(([algoritmo, filas]) => {
      const cuerpo = filas
        .map((f) => {
          const ancho = Math.round(f.porcentaje);
          return `<tr><td class="num">${f.linea}</td><td class="num">${MIL(f.ejecuciones)}</td><td class="num">${fmt(f.porcentaje, 1)} %</td><td><div class="barra-t" style="width:${ancho}%;background:${COLORES[algoritmo] || "#64748b"}"></div></td><td><code>${esc(f.codigo)}</code></td></tr>`;
        })
        .join("");
      return `<article class="grupo-resultado"><h3>${esc(algoritmo)}</h3><div class="tabla-scroll"><table><thead><tr><th>Línea</th><th>Ejecuciones</th><th>% del tiempo</th><th>Peso relativo</th><th>Código</th></tr></thead><tbody>${cuerpo}</tbody></table></div></article>`;
    })
    .join("");
});

const ejecutarScalene = enlazar("scalene", (resultado) => {
  const ficha = (titulo, valor) =>
    `<div class="ficha"><b>${esc(valor)}</b>${esc(titulo)}</div>`;
  el("resumen-scalene").innerHTML =
    ficha("segundos (con el perfilador)", fmt(resultado.segundos, 1)) +
    ficha("memoria pico (MB)", fmt(resultado.memoria_pico_mb, 1)) +
    ficha("de esa memoria, Python (%)", fmt(100 * resultado.fraccion_python, 0));
  llenarTabla(
    el("tabla-scalene").querySelector("tbody"),
    resultado.filas.map((f) => [
      f.archivo,
      { t: f.linea, n: true },
      { t: fmt(f.cpu_python, 1), n: true },
      { t: fmt(f.cpu_nativo, 1), n: true },
      { t: fmt(f.sistema, 1), n: true },
      { t: fmt(f.memoria_pico_mb, 1), n: true },
      { h: `<code>${esc(f.codigo)}</code>` },
    ]),
  );
});

const ejecutarPrediccion = enlazar("prediccion", (datos) => {
  const mejor = (e) => e.reduce((a, b) => (b.error_medio_pct < a.error_medio_pct ? b : a));
  el("resumen-prediccion").innerHTML =
    `<div class="ficha"><b>${datos.entrenamiento}</b>muestras de entrenamiento</div>` +
    `<div class="ficha"><b>${fmt(Math.min(...datos.evaluaciones.map((e) => e.r2_entrenamiento)), 3)}</b>R² mínimo</div>` +
    `<div class="ficha"><b>${fmt(mejor(datos.evaluaciones).error_medio_pct, 1)} %</b>menor error medio (${esc(mejor(datos.evaluaciones).algoritmo)})</div>`;
  llenarTabla(
    el("tabla-evaluaciones").querySelector("tbody"),
    datos.evaluaciones.map((e) => [
      e.algoritmo,
      { t: fmt(e.r2_entrenamiento, 3), n: true },
      { t: fmt(e.error_medio_pct, 1), n: true },
      { t: fmt(e.exponente_nodos, 2), n: true },
      { t: fmt(e.exponente_aristas, 2), n: true },
    ]),
  );
  llenarTabla(
    el("tabla-pruebas-ia").querySelector("tbody"),
    datos.pruebas.map((f) => [
      { t: MIL(f.nodos), n: true },
      { t: MIL(f.aristas), n: true },
      f.algoritmo,
      { t: fmt(f.medido_ms, 2), n: true },
      { t: fmt(f.predicho_ms, 2), n: true },
      { t: fmt(f.error_pct, 1), n: true },
    ]),
  );
  const s = datos.seleccion;
  el("texto-seleccion").textContent =
    `Elegir el algoritmo más rápido entre los correctos para grafos con pesos: ` +
    `el modelo acertó ${s.aciertos_modelo} de ${s.grafos} grafos y la regla fija ` +
    `"siempre ${s.regla_fija}" acertó ${s.aciertos_regla_fija} de ${s.grafos}. ` +
    (s.aciertos_modelo > s.aciertos_regla_fija
      ? "El modelo mejora la regla fija."
      : "El modelo no mejora la regla fija: su aporte es predecir el tiempo, no elegir.");
});

el("btn-recomendar").addEventListener("click", async () => {
  const consulta = new URLSearchParams({
    nodos: el("ia-nodos").value,
    aristas: el("ia-aristas").value,
    ponderado: el("ia-ponderado").checked,
  });
  const texto = el("texto-recomendacion");
  try {
    const r = await api("GET", "/api/analisis/prediccion/recomendar?" + consulta);
    llenarTabla(
      el("tabla-recomendacion").querySelector("tbody"),
      Object.entries(r.predicciones_ms).map(([a, ms]) => [
        a,
        { t: fmt(ms, 2), n: true },
      ]),
    );
    texto.className = "nota";
    texto.textContent =
      `Recomendado: ${r.algoritmo}. ` + r.advertencias.join(" ");
  } catch (error) {
    texto.className = "nota error";
    texto.textContent = error.message;
  }
});

// Al abrir la ventana se ejecuta todo (uno por vez: las mediciones no
// deben solaparse); los botones sirven para repetir una medición.
(async () => {
  for (const ejecutar of [
    ejecutarBenchmark,
    ejecutarCache,
    ejecutarConcurrencia,
    ejecutarPerfilado,
    ejecutarLineas,
    ejecutarScalene,
    ejecutarEntradaSalida,
  ]) {
    await ejecutar();
  }
})();
