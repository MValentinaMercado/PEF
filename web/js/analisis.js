/* Ventana 2: ejecuta las mediciones reales y las muestra. */
const MIL = (n) => Number(n).toLocaleString("es-AR");

/**
 * BFS no maneja pesos: no compite con Dijkstra y A*. Se muestra para conocer
 * el costo base de recorrer el grafo sin manejar pesos y las conclusiones
 * comparan solo a los algoritmos que sí los consideran.
 */
const SIN_PESOS = "BFS";
const USO_BFS =
  "sirve para conocer el costo base de recorrer el grafo sin manejar pesos";
const conPesos = (filas) => filas.filter((f) => f.algoritmo !== SIN_PESOS);
/** Filas con pesos; si no hay ninguna, todas (para no dejar un resumen vacío). */
const comparables = (filas) =>
  conPesos(filas).length ? conPesos(filas) : filas;

/**
 * Devuelve el menor valor de una lista de resultados.
 * Ignora valores nulos, indefinidos y no numéricos.
 */
function mejorResultado(filas, campo) {
  const validas = filas.filter((f) => Number.isFinite(Number(f[campo])));

  if (!validas.length) return null;

  return validas.reduce((mejor, actual) =>
    Number(actual[campo]) < Number(mejor[campo]) ? actual : mejor,
  );
}

/**
 * Devuelve el mayor valor de una lista de resultados.
 */
function mayorResultado(filas, campo) {
  const validas = filas.filter((f) => Number.isFinite(Number(f[campo])));

  if (!validas.length) return null;

  return validas.reduce((mejor, actual) =>
    Number(actual[campo]) > Number(mejor[campo]) ? actual : mejor,
  );
}

/** Conecta un botón con un endpoint y una función que muestra el resultado. */
function enlazar(nombre, mostrar, ruta = nombre) {
  const boton = el("btn-" + nombre),
    estado = el("estado-" + nombre);

  const ejecutar = async () => {
    boton.disabled = true;
    estado.className = "estado";
    estado.textContent = "Ejecutando…";

    const inicio = performance.now();

    try {
      const datos = await api("POST", "/api/analisis/" + ruta);
      mostrar(datos, true);
      guardarResultado(`analisis:${ruta}`, datos);

      estado.textContent =
        "Ejecutado ahora en " +
        fmt((performance.now() - inicio) / 1000, 1) +
        " s.";
    } catch (error) {
      estado.className = "estado error";
      estado.textContent =
        error.message +
        " Los datos visibles, si los hay, son de la última ejecución guardada.";
    }

    boton.disabled = false;
  };

  const guardado = leerResultado(`analisis:${ruta}`);

  if (guardado?.datos) {
    try {
      mostrar(guardado.datos, false);
      estado.textContent = etiquetaResultadoGuardado(guardado);
    } catch (_) {
      guardarResultado(`analisis:${ruta}`, null); // formato antiguo o inválido
    }
  }

  boton.addEventListener("click", ejecutar);
  return ejecutar;
}

// ------------------------------------------------------------ interpretación
// Cada función devuelve el texto de un recuadro .conclusion a partir de los
// datos recibidos o restaurados; no presupone qué algoritmo o modo gana.
const pct = (n) => `${fmt(n, 1)} %`;
const veces = (n) => `${fmt(n, 2)}×`;
const nombreModo = (f) => f.modo;
const enMs = (n) => `${fmt(n, 4)} ms`;
const enKb = (n) => `${fmt(n, 1)} KB`;
const SIN_DATOS = "No hay datos suficientes para interpretar esta tabla.";

/** Compara tiempo, nodos explorados y memoria de un grupo de algoritmos. */
function analizarGrupo(filas) {
  if (filas.length < 2)
    return "Con un solo algoritmo no hay comparación posible.";
  const ponderados = conPesos(filas);
  const base = filas.find((f) => f.algoritmo === SIN_PESOS);
  const frases = [];
  if (ponderados.length > 1) {
    frases.push(
      compararMagnitud(ponderados, (f) => f.tiempo_ms, "Tiempo", enMs),
      compararMagnitud(
        ponderados,
        (f) => f.nodos_explorados,
        "Nodos explorados",
        (n) => MIL(Math.round(n)),
      ),
      compararMagnitud(ponderados, (f) => f.memoria_kb, "Memoria pico", enKb),
    );
  }
  const a = filas.find((f) => f.algoritmo === "A*");
  const d = filas.find((f) => f.algoritmo === "Dijkstra");
  if (
    a &&
    d &&
    a.nodos_explorados < d.nodos_explorados &&
    !casiIguales(a.nodos_explorados, d.nodos_explorados)
  ) {
    const masRapido =
      a.tiempo_ms < d.tiempo_ms && !casiIguales(a.tiempo_ms, d.tiempo_ms);
    frases.push(
      masRapido
        ? "A* exploró menos nodos que Dijkstra y eso se tradujo en menor tiempo."
        : "A* exploró menos nodos que Dijkstra, pero no tardó menos: evaluar la heurística en cada nodo también cuesta.",
    );
  }
  if (base) {
    frases.push(
      `BFS ${USO_BFS}: tardó ${enMs(base.tiempo_ms)}, exploró ${MIL(Math.round(base.nodos_explorados))} nodos y usó ${enKb(base.memoria_kb)} de memoria pico.`,
    );
  }
  return frases.join(" ");
}

/** Resume qué cambia entre los tamaños de grafo del benchmark. */
function analizarBenchmark(filas, grupos) {
  if (!grupos.length) return "";
  const lecturas = grupos.map((n) => {
    const grupo = conPesos(filas.filter((f) => f.nodos === n));
    if (grupo.length < 2) return "sin comparación posible";
    const rapidos = conMenor(grupo, (f) => f.tiempo_ms).filas;
    return rapidos.length === grupo.length
      ? "tiempos similares"
      : `menor tiempo en ${listar(rapidos.map((f) => f.algoritmo))}`;
  });
  const iguales = lecturas.every((l) => l === lecturas[0]);
  const frases = [
    iguales
      ? `Entre Dijkstra y A*, en los ${grupos.length} tamaños medidos: ${lecturas[0]}.`
      : `Entre Dijkstra y A*, ${grupos.map((n, i) => `${MIL(n)} nodos: ${lecturas[i]}`).join("; ")}. El orden en tiempo cambia con el tamaño.`,
  ];
  const primero = grupos[0],
    ultimo = grupos[grupos.length - 1];
  const factor = (algoritmo) => {
    const x = filas.find(
      (f) => f.algoritmo === algoritmo && f.nodos === primero,
    );
    const y = filas.find(
      (f) => f.algoritmo === algoritmo && f.nodos === ultimo,
    );
    return x && y && x.tiempo_ms > 0
      ? `×${fmt(y.tiempo_ms / x.tiempo_ms, 1)}`
      : null;
  };
  const factores = Object.keys(COLORES)
    .filter((algoritmo) => algoritmo !== SIN_PESOS && factor(algoritmo))
    .map((algoritmo) => `${algoritmo} ${factor(algoritmo)}`);
  if (grupos.length > 1 && factores.length) {
    frases.push(
      `Al pasar de ${MIL(primero)} a ${MIL(ultimo)} nodos (×${fmt(ultimo / primero, 0)}) el tiempo se multiplicó por: ${factores.join(", ")}.`,
    );
  }
  if (grupos.length > 1 && factor(SIN_PESOS)) {
    frases.push(
      `BFS ${USO_BFS}: su tiempo se multiplicó por ${factor(SIN_PESOS).slice(1)} en ese mismo cambio de tamaño.`,
    );
  }
  return frases.join(" ");
}

/** Compara lo observado con la curva teórica, algoritmo por algoritmo. */
function analizarEscalabilidad(filas) {
  const frases = [];
  const crecimientoMemoria = [];
  for (const algoritmo of Object.keys(COLORES)) {
    const propias = filas
      .filter((f) => f.algoritmo === algoritmo)
      .sort((a, b) => a.nodos - b.nodos);
    if (propias.length < 2) continue;
    const primera = propias[0],
      ultima = propias[propias.length - 1];
    const razon = ultima.razon;
    const lectura = casiIguales(razon, 1)
      ? "sigue la curva teórica"
      : razon > 1
        ? "crece más rápido que la curva teórica"
        : "crece más lento que la curva teórica";
    let motivo = "";
    if (!casiIguales(razon, 1)) {
      motivo = casiIguales(ultima.razon_explorados, 1)
        ? ", pero su tiempo es proporcional a los nodos explorados: la diferencia viene de cuántos nodos recorre la búsqueda"
        : ", y tampoco coincide al ajustar por nodos explorados: cambió el costo por nodo";
    }
    frases.push(
      `${algoritmo} ${lectura} (a ${MIL(ultima.nodos)} nodos, observado/teórico ${fmt(razon, 2)})${motivo}.`,
    );
    crecimientoMemoria.push(
      `${algoritmo} ×${fmt(ultima.memoria_kb / primera.memoria_kb, 1)}`,
    );
  }
  if (!frases.length) return SIN_DATOS;
  const nodos = filas.map((f) => f.nodos);
  frases.push(
    `La memoria pico se multiplicó por: ${crecimientoMemoria.join(", ")}, mientras los nodos crecieron ×${fmt(Math.max(...nodos) / Math.min(...nodos), 0)}.`,
  );
  return frases.join(" ");
}

/** Interpreta el consumo de memoria y el tiempo de generación de los grafos. */
function analizarGrafos(grafos) {
  if (grafos.length < 2) return SIN_DATOS;
  const orden = [...grafos].sort((a, b) => a.nodos - b.nodos);
  const primero = orden[0],
    ultimo = orden[orden.length - 1];
  const bytes = (g) => (g.memoria_mb * 1024 * 1024) / g.nodos;
  const factorNodos = ultimo.nodos / primero.nodos;
  const factorTiempo = ultimo.segundos / primero.segundos;
  const memoria = casiIguales(bytes(primero), bytes(ultimo))
    ? `El grafo ocupa casi lo mismo por nodo en todos los tamaños (unos ${MIL(Math.round(bytes(ultimo)))} bytes), así que la memoria crece en proporción a su tamaño.`
    : `Los bytes por nodo pasan de ${MIL(Math.round(bytes(primero)))} a ${MIL(Math.round(bytes(ultimo)))}: la memoria no crece en proporción exacta al número de nodos.`;
  const tiempo = casiIguales(factorTiempo, factorNodos)
    ? "El tiempo de generación crece en proporción a los nodos."
    : `El tiempo de generación se multiplicó por ${fmt(factorTiempo, 1)} mientras los nodos crecieron ×${fmt(factorNodos, 0)}: ${factorTiempo > factorNodos ? "más" : "menos"} que proporcional.`;
  return `${memoria} ${tiempo}`;
}

/** Cambio entre dos tamaños de grafo: tiempo = nodos explorados × costo por nodo. */
function crecimiento(filas, desde = 10000, hasta = 100000) {
  const factorLog = Math.log2(hasta) / Math.log2(desde);
  return Object.keys(COLORES).flatMap((algoritmo) => {
    const a = filas.find((f) => f.algoritmo === algoritmo && f.nodos === desde);
    const b = filas.find((f) => f.algoritmo === algoritmo && f.nodos === hasta);
    if (!a || !b) return [];
    return [
      {
        algoritmo,
        desde,
        hasta,
        tiempo: b.tiempo_ms / a.tiempo_ms,
        explorados: b.nodos_explorados / a.nodos_explorados,
        costo: b.us_por_nodo / a.us_por_nodo,
        esperado: algoritmo === "BFS" ? 1 : factorLog,
      },
    ];
  });
}

/** Separa el crecimiento del tiempo y lo contrasta con el factor esperado. */
function analizarCrecimiento(datos) {
  if (!datos.length)
    return "Faltan las mediciones de 10.000 y 100.000 nodos para analizar el crecimiento.";
  const frases = datos.map((d) => {
    const base = `${d.algoritmo}: el tiempo se multiplicó por ${fmt(d.tiempo, 2)} (×${fmt(d.explorados, 2)} por nodos explorados y ×${fmt(d.costo, 2)} por costo por nodo)`;
    let lectura;
    if (casiIguales(d.costo, d.esperado)) {
      lectura =
        d.algoritmo === "BFS"
          ? "el costo por nodo se mantuvo, como predice O(V+E)"
          : "el costo por nodo crece como predice el factor log V";
    } else if (d.costo > d.esperado) {
      lectura = `el costo por nodo creció más de lo esperado (×${fmt(d.esperado, 2)}); puede deberse a efectos de caché de CPU y memoria`;
    } else {
      lectura = `el costo por nodo creció menos de lo esperado (×${fmt(d.esperado, 2)})`;
    }
    return `${base}; ${lectura}.`;
  });
  return frases.join(" ");
}

/** Interpreta el experimento de caché frente a lo máximo posible. */
function analizarCache(r) {
  const maximo = r.total_consultas - r.pares_distintos;
  const tasa =
    r.total_consultas > 0 ? (100 * r.aciertos) / r.total_consultas : 0;
  const aprovechamiento =
    r.aciertos >= maximo
      ? "es el máximo posible, porque solo la primera consulta de cada par distinto debe calcularse"
      : `el máximo posible con ${r.pares_distintos} pares distintos era ${maximo}`;
  const [tSin, mSin] = r.sin_cache,
    [tCon, mCon] = r.con_cache;
  const tiempo = casiIguales(tSin, tCon)
    ? "La caché no cambió el tiempo de forma apreciable."
    : tCon < tSin
      ? `Con caché el tiempo fue ${fmt(tSin / tCon, 1)} veces menor.`
      : "Con caché el tiempo fue mayor.";
  const memoria = casiIguales(mSin, mCon)
    ? "La memoria pico fue similar."
    : `La caché ${mCon > mSin ? "agregó" : "ahorró"} ${enKb(Math.abs(mCon - mSin))} de memoria pico.`;
  const comprobaciones = [
    r.fallo_tras_cambio
      ? "Al modificar el grafo la caché se invalidó, como se esperaba."
      : "Al modificar el grafo no hubo el fallo esperado: conviene revisar la invalidación.",
    r.acierto_al_repetir
      ? "Una consulta repetida se resolvió desde la caché."
      : "Una consulta repetida no produjo un acierto de caché.",
  ];
  return `${r.aciertos} de ${r.total_consultas} consultas (${pct(tasa)}) salieron de la caché; ${aprovechamiento}. ${tiempo} ${memoria} ${comprobaciones.join(" ")}`;
}

/** Frases de cada modo frente a uno de referencia, según su aceleración. */
function compararConBase(filas, base) {
  return filas
    .filter((f) => f !== base)
    .map((f) => {
      if (casiIguales(f.aceleracion, 1))
        return `${f.modo} tardó prácticamente lo mismo que ${base.modo}.`;
      return f.aceleracion > 1
        ? `${f.modo} fue ${veces(f.aceleracion)} más rápido que ${base.modo}.`
        : `${f.modo} fue ${veces(1 / f.aceleracion)} más lento que ${base.modo}.`;
    });
}

/** Contrasta hilos y procesos sin suponer cuál acelera. */
function lecturaParalelismo(filas) {
  const clara = (f) => f && f.aceleracion > 1 && !casiIguales(f.aceleracion, 1);
  const hilos = filas.find((f) => f.modo.startsWith("Hilos"));
  const procesos = filas.find((f) => f.modo.startsWith("Procesos"));
  if (!hilos || !procesos) return "";
  if (!clara(hilos) && clara(procesos))
    return "Los procesos aceleraron y los hilos no, lo esperable en trabajo de CPU con GIL.";
  if (!clara(hilos) && !clara(procesos))
    return "Ni hilos ni procesos aceleraron: en esta carga el costo de coordinarlos supera la ganancia.";
  if (clara(hilos) && !clara(procesos))
    return "Los hilos aceleraron y los procesos no: el costo de crear procesos y transferir datos pesó más que la ganancia.";
  return "Tanto hilos como procesos aceleraron en esta ejecución.";
}

function analizarConcurrencia(filas) {
  if (filas.length < 2) return SIN_DATOS;
  const base = filas.find((f) => f.modo === "Secuencial") || filas[0];
  return [
    ...compararConBase(filas, base),
    lecturaParalelismo(filas),
    compararMagnitud(
      filas,
      (f) => f.memoria_kb,
      "Memoria pico",
      enKb,
      nombreModo,
    ),
  ]
    .filter(Boolean)
    .join(" ");
}

/** Escritura o lectura: cada modo frente al primero, más la memoria. */
function analizarModosArchivo(filas, inicio = "") {
  if (filas.length < 2) return SIN_DATOS;
  return [
    inicio,
    ...compararConBase(filas, filas[0]),
    compararMagnitud(
      filas,
      (f) => f.memoria_kb,
      "Memoria pico",
      enKb,
      nombreModo,
    ),
  ]
    .filter(Boolean)
    .join(" ");
}

function analizarParalelo(r) {
  if (r.paralelo.length < 2) return SIN_DATOS;
  const base = r.paralelo.find((f) => f.modo === "Secuencial") || r.paralelo[0];
  const coincide = r.resultados_coinciden
    ? "Todos los modos produjeron el mismo resultado."
    : "Atención: los resultados de los modos no coinciden.";
  return [
    ...compararConBase(r.paralelo, base),
    lecturaParalelismo(r.paralelo),
    coincide,
  ]
    .filter(Boolean)
    .join(" ");
}

/** Dónde se concentra el tiempo propio de un algoritmo (cProfile). */
function analizarFunciones(funciones) {
  const total = funciones.reduce((suma, f) => suma + f.tiempo_propio, 0);
  if (!funciones.length || total <= 0)
    return "No se registró tiempo para analizar.";
  const orden = [...funciones].sort(
    (a, b) => b.tiempo_propio - a.tiempo_propio,
  );
  const cima = orden.filter((f) =>
    casiIguales(f.tiempo_propio, orden[0].tiempo_propio),
  );
  const frases = [
    cima.length > 1
      ? `${listar(cima.map((f) => f.funcion))} concentran un tiempo propio similar (${porcentajeDe(orden[0].tiempo_propio, total)} del total cada una).`
      : `${orden[0].funcion} concentra ${porcentajeDe(orden[0].tiempo_propio, total)} del tiempo propio.`,
  ];
  const frecuente = mayorResultado(funciones, "llamadas");
  if (frecuente && !cima.includes(frecuente)) {
    frases.push(
      `La más llamada es ${frecuente.funcion} (${MIL(frecuente.llamadas)} veces) y solo aporta ${porcentajeDe(frecuente.tiempo_propio, total)}: llamar mucho no implica costar mucho.`,
    );
  }
  return frases.join(" ");
}

function analizarMemoria(filas) {
  if (!filas.length) return "memory_profiler no devolvió líneas para analizar.";
  const mayor = mayorResultado(filas, "incremento_mib");
  const maxima = Math.max(...filas.map((f) => f.memoria_mib));
  const aviso =
    "memory_profiler mide el proceso completo, por eso la memoria total incluye lo que ya estaba cargado.";
  if (!mayor || mayor.incremento_mib < 0.05) {
    return `Ninguna línea muestra un incremento visible a un decimal (el máximo total es ${fmt(maxima, 1)} MiB). ${aviso}`;
  }
  const suma = filas.reduce((s, f) => s + Math.max(f.incremento_mib, 0), 0);
  return `La línea ${mayor.linea} aporta el mayor incremento (${fmt(mayor.incremento_mib, 1)} MiB, ${porcentajeDe(mayor.incremento_mib, suma)} de los incrementos): ${mayor.codigo.trim()}. ${aviso}`;
}

function analizarLineas(filas) {
  if (!filas.length) return "No se registraron líneas para analizar.";
  const orden = [...filas].sort((a, b) => b.porcentaje - a.porcentaje);
  const tres = orden.slice(0, 3).reduce((s, f) => s + f.porcentaje, 0);
  return `La línea ${orden[0].linea} concentra ${pct(orden[0].porcentaje)} del tiempo (${orden[0].codigo.trim()}); las ${Math.min(3, orden.length)} más pesadas suman ${pct(tres)}. El perfilador distorsiona los tiempos absolutos: sirve para comparar líneas entre sí.`;
}

function analizarScalene(r) {
  if (!r.filas.length) return "Scalene no devolvió líneas para analizar.";
  const total = (f) => f.cpu_python + f.cpu_nativo + f.sistema;
  const cima = r.filas.reduce((m, f) => (total(f) > total(m) ? f : m));
  const suma = (campo) => r.filas.reduce((s, f) => s + f[campo], 0);
  const partes = [
    ["Python", suma("cpu_python")],
    ["nativo", suma("cpu_nativo")],
    ["sistema", suma("sistema")],
  ];
  const mayor = partes.reduce((m, p) => (p[1] > m[1] ? p : m));
  const memoria =
    r.fraccion_python >= 0.5
      ? "La mayor parte de la memoria pico corresponde a objetos de Python."
      : "La mayor parte de la memoria pico no es de Python (es memoria nativa).";
  return `La línea más costosa es ${cima.archivo}:${cima.linea} (${pct(total(cima))} del tiempo). Entre las líneas mostradas predomina el CPU ${mayor[0]} (${partes.map(([n, v]) => `${n} ${pct(v)}`).join(", ")}). ${memoria}`;
}

function analizarEvaluaciones(evaluaciones) {
  if (!evaluaciones.length) return SIN_DATOS;
  const ponderadas = comparables(evaluaciones);
  const base = evaluaciones.find((e) => e.algoritmo === SIN_PESOS);
  const crecimientoDe = (e) => {
    const suma = e.exponente_nodos + e.exponente_aristas;
    const forma = casiIguales(suma, 1)
      ? "casi lineal"
      : suma > 1
        ? "más que lineal"
        : "menos que lineal";
    return `${fmt(suma, 2)} (${forma})`;
  };
  const peor = ponderadas.reduce((m, e) =>
    e.r2_entrenamiento < m.r2_entrenamiento ? e : m,
  );
  const ajuste = casiIguales(peor.r2_entrenamiento, 1)
    ? `El ajuste es alto en Dijkstra y A* (R² mínimo ${fmt(peor.r2_entrenamiento, 3)}).`
    : `Entre Dijkstra y A*, el ajuste más flojo es el de ${peor.algoritmo} (R² ${fmt(peor.r2_entrenamiento, 3)}).`;
  const formas = ponderadas.map((e) => `${e.algoritmo} ${crecimientoDe(e)}`);
  const frases = [ajuste];
  if (ponderadas.length > 1) {
    frases.push(
      compararMagnitud(
        ponderadas,
        (e) => e.error_medio_pct,
        "Error medio en grafos nuevos",
        pct,
      ),
    );
  }
  frases.push(
    `Suma de exponentes b+c, que describe el crecimiento si nodos y aristas aumentan a la vez: ${formas.join(", ")}.`,
  );
  if (base && ponderadas !== evaluaciones) {
    frases.push(
      `BFS ${USO_BFS}: R² ${fmt(base.r2_entrenamiento, 3)}, error medio ${pct(base.error_medio_pct)} y suma de exponentes ${crecimientoDe(base)}.`,
    );
  }
  return frases.join(" ");
}

function analizarPruebasIa(pruebas, s) {
  if (!pruebas.length) return SIN_DATOS;
  const considerar = comparables(pruebas);
  const peor = mayorResultado(considerar, "error_pct");
  const sobre = considerar.filter((p) => p.predicho_ms > p.medido_ms).length;
  const sesgo = casiIguales(sobre, considerar.length - sobre)
    ? "no muestra un sesgo claro entre sobreestimar y subestimar"
    : sobre > considerar.length - sobre
      ? `tiende a sobreestimar (${sobre} de ${considerar.length})`
      : `tiende a subestimar (${considerar.length - sobre} de ${considerar.length})`;
  const diferencia = s.aciertos_modelo - s.aciertos_regla_fija;
  const eleccion =
    diferencia === 0
      ? "iguala a la regla fija"
      : diferencia > 0
        ? "supera a la regla fija"
        : "queda por debajo de la regla fija";
  return `El mayor error fue ${pct(peor.error_pct)} (${peor.algoritmo}, ${MIL(peor.nodos)} nodos) y el modelo ${sesgo}. Eligiendo el algoritmo correcto acertó ${s.aciertos_modelo} de ${s.grafos} grafos frente a ${s.aciertos_regla_fija} de la regla fija (${s.regla_fija}): ${eleccion}.`;
}

function analizarRecomendacion(r) {
  const filas = Object.entries(r.predicciones_ms).map(
    ([algoritmo, tiempo]) => ({ algoritmo, tiempo }),
  );
  const parecidos = conMenor(filas, (f) => f.tiempo).filas;
  const lectura =
    parecidos.length > 1
      ? `${listar(parecidos.map((f) => f.algoritmo))} tienen predicciones similares: la recomendación de ${r.algoritmo} se apoya en una diferencia mínima.`
      : `${r.algoritmo} es el de menor tiempo predicho.`;
  return `${lectura} ${r.advertencias.join(" ")}`.trim();
}

function analizarEntrenamiento(d) {
  const razon = (d.recoleccion_s * 1000) / d.ajuste_ms;
  const reparto = casiIguales(razon, 1)
    ? "Medir los datos y ajustar el modelo cuestan algo similar."
    : razon > 1
      ? `Medir los datos cuesta ${fmt(razon, 0)} veces más que ajustar el modelo: el costo está en medir, no en calcular.`
      : `Ajustar el modelo cuesta ${fmt(1 / razon, 1)} veces más que medir los datos.`;
  return `${avisoEntrenado(d)}${reparto} El ajuste llega a un pico de ${fmt(d.memoria_ajuste_kb, 0)} KB y el modelo resultante pesa ${fmt(d.tamano_modelo_bytes / 1024, 1)} KB.`;
}

function analizarPrecision(d) {
  if (!d.filas.length) return avisoEntrenado(d) + SIN_DATOS;
  const lecturas = d.filas.map((f) => {
    if (casiIguales(f.error_medio_pct, f.error_referencia_pct))
      return `${f.algoritmo}: el modelo no mejora la referencia (${pct(f.error_medio_pct)})`;
    return f.error_medio_pct < f.error_referencia_pct
      ? `${f.algoritmo}: el modelo baja el error de ${pct(f.error_referencia_pct)} a ${pct(f.error_medio_pct)}`
      : `${f.algoritmo}: el modelo es peor que la referencia (${pct(f.error_medio_pct)} frente a ${pct(f.error_referencia_pct)})`;
  });
  return `${avisoEntrenado(d)}${lecturas.join("; ")}.`;
}

function analizarLatencia(d) {
  const razon = d.recomendacion_us / d.prediccion_us;
  const relacion = casiIguales(razon, 1)
    ? "cuesta lo mismo"
    : `cuesta ${fmt(razon, 1)} veces ${razon > 1 ? "más" : "menos"}`;
  const escala =
    Math.max(d.prediccion_us, d.recomendacion_us) < 1000
      ? "Ambas tardan menos de 1 ms."
      : "Alguna de las dos supera 1 ms.";
  return `${avisoEntrenado(d)}Una predicción tarda ${fmt(d.prediccion_us, 0)} µs y una recomendación ${relacion} que una predicción, porque evalúa varios algoritmos. ${escala} El pico de memoria es de ${enKb(d.memoria_kb)}.`;
}

function analizarComparacion(d) {
  if (!d.filas.length) return avisoEntrenado(d) + SIN_DATOS;
  const filas = [...d.filas].sort((a, b) => a.nodos - b.nodos);
  const claras = filas.filter(
    (f) => f.veces_mas_rapida > 1 && !casiIguales(f.veces_mas_rapida, 1),
  );
  const rango = (campo) =>
    `${fmt(Math.min(...filas.map((f) => f[campo])), 1)} a ${fmt(Math.max(...filas.map((f) => f[campo])), 1)}`;
  let rapidez;
  if (claras.length === filas.length)
    rapidez = `Predecir fue más rápido que ejecutar Dijkstra en todos los tamaños (${rango("veces_mas_rapida")} veces).`;
  else if (!claras.length)
    rapidez =
      "Predecir no fue más rápido que ejecutar Dijkstra en ningún tamaño medido.";
  else
    rapidez = `Predecir fue más rápido en ${claras.length} de ${filas.length} tamaños, desde ${MIL(claras[0].nodos)} nodos.`;
  const amortizacion =
    d.estimaciones_para_amortizar === null
      ? "Con estas mediciones el entrenamiento no llega a amortizarse."
      : `Entrenar (${fmt(d.costo_entrenamiento_ms / 1000, 1)} s) se amortiza tras unas ${MIL(d.estimaciones_para_amortizar)} estimaciones.`;
  return `${avisoEntrenado(d)}${rapidez} El error de la predicción va de ${rango("error_pct")} %. ${amortizacion}`;
}

/** Escribe el texto de un recuadro de interpretación. */
const interpretar = (id, texto) => {
  el(id).textContent = texto;
};

/** Gráfico SVG sencillo para comparar una métrica entre algoritmos. */
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

    svg += `<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(h, 1)}" fill="${colores[f.algoritmo] || "#9a948c"}"><title>${f.algoritmo}: ${fmt(v, 4)}</title></rect><text x="${x + bw / 2}" y="${H - bottom + 17}" text-anchor="middle" font-size="11" fill="currentColor">${f.algoritmo}</text>`;
  });

  return svg + "</svg>";
}

function tarjetaBenchmark(nodos, filas) {
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

  return `<article class="grupo-resultado">
    <h3>${MIL(nodos)} nodos</h3>
    <div class="tabla-scroll">
      <table>
        <thead>
          <tr>
            <th>Algoritmo</th>
            <th>Tiempo medio (ms)</th>
            <th>Memoria pico (KB)</th>
            <th>Nodos explorados</th>
          </tr>
        </thead>
        <tbody>${tr}</tbody>
      </table>
    </div>
    <div class="graficos-grupo">${graficos}</div>
    <p class="conclusion">${esc(analizarGrupo(filas))}</p>
    <pre class="salida-consola">${esc(salida)}</pre>
  </article>`;
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

  interpretar("analisis-benchmark", analizarBenchmark(filas, grupos));
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

  interpretar("texto-cache", analizarCache(r));
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

  interpretar("texto-concurrencia", analizarConcurrencia(filas));
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

  interpretar(
    "analisis-escritura",
    analizarModosArchivo(
      r.escritura,
      `Archivo de ${MIL(Math.round(r.tamano_kb))} KB y ${MIL(r.lineas)} líneas.`,
    ),
  );
  interpretar("analisis-lectura", analizarModosArchivo(r.lectura));
  interpretar("analisis-paralelo", analizarParalelo(r));
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

const ejecutarPerfilado = enlazar("perfilado", ({ cpu, memoria }, ahora) => {
  if (ahora) void prepararSnakeviz(Object.keys(cpu));
  else
    el("estado-snakeviz").textContent =
      "SnakeViz se inicia al ejecutar el perfilado.";

  const nombres = { BFS: "BFS", Dijkstra: "Dijkstra", "A*": "A*" };

  el("resultados-perfilado").innerHTML = Object.entries(cpu)
    .map(([algoritmo, funciones]) => {
      const maximo = Math.max(...funciones.map((f) => f.tiempo_propio), 1e-12);

      const filas = funciones
        .map((f) => {
          const ancho = Math.round((100 * f.tiempo_propio) / maximo);

          return `<tr>
            <td>${esc(f.funcion)}</td>
            <td>${MIL(f.llamadas)}</td>
            <td>${fmt(f.tiempo_propio, 6)}</td>
            <td>${fmt(f.tiempo_acumulado, 6)}</td>
            <td><div class="barra-t" style="width:${ancho}%;background:${COLORES[algoritmo] || "#9a948c"}"></div></td>
          </tr>`;
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

      return `<article class="grupo-resultado">
        <h3>${nombres[algoritmo] || esc(algoritmo)}</h3>
        <div class="tabla-scroll">
          <table>
            <thead>
              <tr>
                <th>Función</th>
                <th>Llamadas</th>
                <th>Tiempo propio (s)</th>
                <th>Tiempo acumulado (s)</th>
                <th>Peso relativo</th>
              </tr>
            </thead>
            <tbody>${filas}</tbody>
          </table>
        </div>
        <p class="conclusion">${esc(analizarFunciones(funciones))}</p>
        <pre class="salida-consola">${esc(salida)}</pre>
      </article>`;
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
  interpretar("analisis-memoria", analizarMemoria(memoria));

  el("salida-memoria").textContent =
    memoria
      .map(
        (f) =>
          `Línea ${f.linea}: ${fmt(f.memoria_mib, 1)} MiB (${fmt(f.incremento_mib, 1)} MiB) — ${f.codigo}`,
      )
      .join("\n") || "memory_profiler no devolvió líneas para mostrar.";
});

/** Gráfico SVG con ejes logarítmicos: tiempo observado y esperado. */
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
    arriba + (1 - (Math.log10(v) - y0) / (y1 - y0 || 1)) * (H - arriba - abajo);

  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Tiempo observado y esperado según la cantidad de nodos" style="max-width:${W}px;width:100%">`;

  for (let e = y0; e <= y1; e++) {
    const y = Y(10 ** e);

    svg += `<line x1="${izq}" x2="${W - der}" y1="${y}" y2="${y}" stroke="#9a948c" stroke-opacity=".25"/><text x="${izq - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="currentColor">${MIL(10 ** e)}</text>`;
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

enlazar("escalabilidad", ({ filas, grafos }) => {
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

  const cambios = crecimiento(filas);
  const aVeces = (n) => ({ t: fmt(n, 2) + " ×", n: true });
  llenarTabla(
    el("tabla-descomposicion").querySelector("tbody"),
    cambios.map((c) => [
      c.algoritmo,
      aVeces(c.tiempo),
      aVeces(c.explorados),
      aVeces(c.costo),
      aVeces(c.esperado),
    ]),
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

  interpretar("analisis-escalabilidad", analizarEscalabilidad(filas));
  interpretar("analisis-grafos", analizarGrafos(grafos));
  interpretar("analisis-descomposicion", analizarCrecimiento(cambios));
});
const ejecutarLineas = enlazar("lineas", (algoritmos) => {
  el("resultados-lineas").innerHTML = Object.entries(algoritmos)
    .map(([algoritmo, filas]) => {
      const cuerpo = filas
        .map((f) => {
          const ancho = Math.round(f.porcentaje);

          return `<tr>
            <td class="num">${f.linea}</td>
            <td class="num">${MIL(f.ejecuciones)}</td>
            <td class="num">${fmt(f.porcentaje, 1)} %</td>
            <td><div class="barra-t" style="width:${ancho}%;background:${COLORES[algoritmo] || "#9a948c"}"></div></td>
            <td><code>${esc(f.codigo)}</code></td>
          </tr>`;
        })
        .join("");

      return `<article class="grupo-resultado">
        <h3>${esc(algoritmo)}</h3>
        <div class="tabla-scroll">
          <table>
            <thead>
              <tr>
                <th>Línea</th>
                <th>Ejecuciones</th>
                <th>% del tiempo</th>
                <th>Peso relativo</th>
                <th>Código</th>
              </tr>
            </thead>
            <tbody>${cuerpo}</tbody>
          </table>
        </div>
        <p class="conclusion">${esc(analizarLineas(filas))}</p>
      </article>`;
    })
    .join("");
});

const ejecutarScalene = enlazar("scalene", (resultado) => {
  el("resumen-scalene").innerHTML =
    ficha("segundos (con el perfilador)", fmt(resultado.segundos, 1)) +
    ficha("memoria pico (MB)", fmt(resultado.memoria_pico_mb, 1)) +
    ficha(
      "de esa memoria, Python (%)",
      fmt(100 * resultado.fraccion_python, 0),
    );

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
  interpretar("analisis-scalene", analizarScalene(resultado));
});

enlazar("prediccion", (datos) => {
  const comparadas = comparables(datos.evaluaciones);
  const mejor = mejorResultado(comparadas, "error_medio_pct");

  el("resumen-prediccion").innerHTML =
    `<div class="ficha"><b>${datos.entrenamiento}</b> muestras de entrenamiento</div>` +
    `<div class="ficha"><b>${fmt(Math.min(...comparadas.map((e) => e.r2_entrenamiento)), 3)}</b> R² mínimo (Dijkstra y A*)</div>` +
    (mejor
      ? `<div class="ficha"><b>${fmt(mejor.error_medio_pct, 1)} %</b> menor error medio (${esc(mejor.algoritmo)})</div>`
      : "");

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

  interpretar(
    "analisis-evaluaciones",
    analizarEvaluaciones(datos.evaluaciones),
  );
  interpretar(
    "texto-seleccion",
    analizarPruebasIa(datos.pruebas, datos.seleccion),
  );
});

/** Muestra la recomendación de una consulta (nueva o restaurada). */
function mostrarRecomendacion(r) {
  llenarTabla(
    el("tabla-recomendacion").querySelector("tbody"),
    Object.entries(r.predicciones_ms).map(([algoritmo, tiempo]) => [
      algoritmo,
      { t: fmt(tiempo, 2), n: true },
    ]),
  );
  const texto = el("texto-recomendacion");
  texto.className = "conclusion";
  texto.textContent = analizarRecomendacion(r);
}

el("btn-recomendar").addEventListener("click", async () => {
  const consulta = {
    nodos: el("ia-nodos").value,
    aristas: el("ia-aristas").value,
    ponderado: el("ia-ponderado").checked,
  };
  const texto = el("texto-recomendacion");
  try {
    const r = await api(
      "GET",
      "/api/analisis/prediccion/recomendar?" + new URLSearchParams(consulta),
    );
    mostrarRecomendacion(r);
    guardarResultado("analisis:recomendar", { consulta, r });
    el("estado-recomendar").textContent = "Consulta realizada ahora.";
  } catch (error) {
    texto.className = "conclusion";
    texto.textContent = error.message;
  }
});

const recomendacionGuardada = leerResultado("analisis:recomendar");
if (recomendacionGuardada?.datos?.r) {
  const { consulta, r } = recomendacionGuardada.datos;
  try {
    mostrarRecomendacion(r);
    el("ia-nodos").value = consulta.nodos;
    el("ia-aristas").value = consulta.aristas;
    el("ia-ponderado").checked = consulta.ponderado;
    el("estado-recomendar").textContent = etiquetaResultadoGuardado(
      recomendacionGuardada,
    );
  } catch (_) {
    guardarResultado("analisis:recomendar", null); // formato antiguo o inválido
  }
}

/** Aviso cuando la medición tuvo que entrenar el modelo antes. */
const avisoEntrenado = (datos) =>
  datos.entrenado_ahora
    ? "El modelo no estaba entrenado: se entrenó antes de medir. "
    : "";

enlazar(
  "modelo-entrenamiento",
  (d) => {
    el("resumen-modelo-entrenamiento").innerHTML =
      ficha("muestras medidas", MIL(d.muestras)) +
      ficha("s para medir los datos", fmt(d.recoleccion_s, 1)) +
      ficha("ms para ajustar (fit)", fmt(d.ajuste_ms, 1)) +
      ficha("KB de memoria pico", fmt(d.memoria_ajuste_kb, 0)) +
      ficha("KB pesa el modelo", fmt(d.tamano_modelo_bytes / 1024, 1));

    interpretar("conclusion-modelo-entrenamiento", analizarEntrenamiento(d));
  },
  "modelo/entrenamiento",
);

enlazar(
  "modelo-precision",
  (d) => {
    llenarTabla(
      el("tabla-modelo-precision").querySelector("tbody"),
      d.filas.map((f) => [
        f.algoritmo,
        { t: f.grafos, n: true },
        { t: fmt(f.mae_ms, 2), n: true },
        { t: fmt(f.error_medio_pct, 1), n: true },
        { t: fmt(f.mae_referencia_ms, 2), n: true },
        { t: fmt(f.error_referencia_pct, 1), n: true },
      ]),
    );

    interpretar("conclusion-modelo-precision", analizarPrecision(d));
  },
  "modelo/precision",
);

enlazar(
  "modelo-latencia",
  (d) => {
    el("resumen-modelo-latencia").innerHTML =
      ficha("µs por predicción", fmt(d.prediccion_us, 0)) +
      ficha("µs por recomendación", fmt(d.recomendacion_us, 0)) +
      ficha("KB de memoria pico", fmt(d.memoria_kb, 1));

    interpretar("conclusion-modelo-latencia", analizarLatencia(d));
  },
  "modelo/latencia",
);

enlazar(
  "modelo-comparacion",
  (d) => {
    llenarTabla(
      el("tabla-modelo-comparacion").querySelector("tbody"),
      d.filas.map((f) => [
        { t: MIL(f.nodos), n: true },
        { t: MIL(f.aristas), n: true },
        { t: fmt(f.directo_ms, 3), n: true },
        { t: fmt(f.predicho_ms, 3), n: true },
        { t: fmt(f.error_pct, 1), n: true },
        { t: fmt(f.prediccion_us, 0), n: true },
        { t: fmt(f.veces_mas_rapida, 1), n: true },
      ]),
    );

    el("resumen-modelo-comparacion").innerHTML =
      ficha("s costó entrenar", fmt(d.costo_entrenamiento_ms / 1000, 1)) +
      ficha(
        "estimaciones para amortizar",
        d.estimaciones_para_amortizar === null
          ? "no se amortiza"
          : MIL(d.estimaciones_para_amortizar),
      );

    interpretar("conclusion-modelo-comparacion", analizarComparacion(d));
  },
  "modelo/comparacion",
);

// Las mediciones se ejecutan únicamente desde sus botones.
