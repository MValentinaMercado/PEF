"""Escritura y lectura de archivos grandes: buffer, batching y paralelismo.

El archivo de ejemplo es una lista de aristas, una por línea::

    origen,destino,peso

Se comparan tres técnicas, siempre con mediciones reales:

* **Buffer** al escribir: acumular líneas en memoria y escribirlas juntas.
* **Batching** al leer: recorrer el archivo en lotes de ``N`` líneas en vez
  de cargarlo entero o de hacer una operación por línea.
* **Procesamiento en paralelo** de los lotes con hilos o procesos.
"""

import math
import random
import tempfile
import time
from collections import Counter, deque
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import (
    Executor,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
)
from itertools import islice
from pathlib import Path
from typing import NamedTuple, TextIO, TypeVar

from rutas.mediciones import medir_tiempo_y_memoria

T = TypeVar("T")
LINEAS_ARCHIVO = 100_000
TAMANO_LOTE = 1000  # líneas por buffer / lote al escribir y al leer
TAMANO_LOTE_PARALELO = (
    5000  # lotes más grandes amortizan el envío entre procesos
)
BYTES_POR_KB = 1024


class FilaMedida(NamedTuple):
    """Resultado de un modo de escritura o de lectura."""

    modo: str
    tiempo_ms: float
    memoria_kb: float
    lineas: int
    aceleracion: float  # tiempo del primer modo / tiempo de este modo


class FilaParalelo(NamedTuple):
    """Resultado de un modo de procesamiento por lotes."""

    modo: str
    tiempo_ms: float
    lotes: int
    lineas: int
    aceleracion: float  # tiempo secuencial / tiempo de este modo


class ResumenArchivo(NamedTuple):
    """Lo que se calcula de cada lote (y del archivo completo al combinarlos).

    Atributos:
        lineas: cantidad de aristas leídas.
        suma_pesos: suma de los pesos de todas las aristas.
        grados: cuántas aristas toca cada nodo.
    """

    lineas: int
    suma_pesos: float
    grados: Counter


class ResultadoEntradaSalida(NamedTuple):
    """Las tres tablas del experimento y la comprobación de resultados."""

    lineas: int
    tamano_kb: float
    tamano_lote: int
    tamano_lote_paralelo: int
    trabajadores: int
    escritura: list[FilaMedida]
    lectura: list[FilaMedida]
    paralelo: list[FilaParalelo]
    resultados_coinciden: bool


# --------------------------------------------------------------------------
# Generación y escritura
# --------------------------------------------------------------------------


def generar_lineas(cantidad: int, semilla: int = 1) -> Iterator[str]:
    """Genera ``cantidad`` aristas ``origen,destino,peso`` de a una.

    Es un generador: nunca guarda todas las líneas en memoria.

    >>> list(generar_lineas(2, 1)) == list(generar_lineas(2, 1))
    True
    >>> len(list(generar_lineas(5)))
    5
    >>> next(generar_lineas(1)).count(",")
    2
    """
    azar = random.Random(semilla)
    nodos = max(2, cantidad // 4)
    for _ in range(cantidad):
        origen = azar.randrange(nodos)
        destino = (origen + 1 + azar.randrange(nodos - 1)) % nodos  # != origen
        yield f"{origen},{destino},{azar.uniform(1, 500):.2f}\n"


def escribir_sin_buffer(ruta: Path, lineas: Iterable[str]) -> int:
    """Una operación de escritura por línea; devuelve cuántas escribió.

    Python ya agrupa las escrituras internamente; por eso se fuerza un
    ``flush()`` tras cada línea, que equivale a una operación de E/S por
    registro (el peor caso que el buffer intenta evitar).
    """
    total = 0
    with open(ruta, "w", encoding="utf-8") as archivo:
        for linea in lineas:
            archivo.write(linea)
            archivo.flush()
            total += 1
    return total


def escribir_con_buffer(
    ruta: Path, lineas: Iterable[str], tamano_buffer: int = TAMANO_LOTE
) -> int:
    """Acumula líneas y las escribe de a ``tamano_buffer`` (``writelines``)."""
    buffer: list[str] = []
    total = 0
    with open(ruta, "w", encoding="utf-8") as archivo:
        for linea in lineas:
            buffer.append(linea)
            if len(buffer) >= tamano_buffer:
                archivo.writelines(buffer)
                total += len(buffer)
                buffer.clear()
        if buffer:  # lo que quedó sin completar un lote
            archivo.writelines(buffer)
            total += len(buffer)
    return total


def escribir_todo_junto(ruta: Path, lineas: Iterable[str]) -> int:
    """Junta todo en memoria y hace un único ``write`` (rápido, O(n) RAM)."""
    texto = "".join(lineas)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(texto)
    return texto.count("\n")


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------


def _sumar_pesos(lineas: Iterable[str]) -> tuple[int, float]:
    """Cuenta las líneas y suma el último campo (el peso)."""
    total, suma = 0, 0.0
    for linea in lineas:
        suma += float(linea.rsplit(",", 1)[1])
        total += 1
    return total, suma


def leer_todo(ruta: Path) -> tuple[int, float]:
    """Carga el archivo completo con ``read()``; la memoria crece con él."""
    with open(ruta, encoding="utf-8") as archivo:
        return _sumar_pesos(archivo.read().splitlines())


def leer_linea_a_linea(ruta: Path) -> tuple[int, float]:
    """Itera el archivo línea por línea: memoria constante."""
    with open(ruta, encoding="utf-8") as archivo:
        return _sumar_pesos(archivo)


def leer_en_lotes(
    archivo: TextIO, tamano_lote: int = TAMANO_LOTE
) -> Iterator[list[str]]:
    """Genera listas de hasta ``tamano_lote`` líneas hasta agotar el archivo.

    El último lote puede ser más corto y nunca se devuelven lotes vacíos.

    >>> import io
    >>> texto = io.StringIO("a\\nb\\nc\\nd\\ne\\n")
    >>> [len(lote) for lote in leer_en_lotes(texto, 2)]
    [2, 2, 1]
    >>> list(leer_en_lotes(io.StringIO("")))
    []
    """
    while lote := list(islice(archivo, tamano_lote)):
        yield lote


def leer_por_lotes(
    ruta: Path, tamano_lote: int = TAMANO_LOTE
) -> tuple[int, float]:
    """Lee en lotes y procesa cada lote antes de pedir el siguiente."""
    total, suma = 0, 0.0
    with open(ruta, encoding="utf-8") as archivo:
        for lote in leer_en_lotes(archivo, tamano_lote):
            lineas, peso = _sumar_pesos(lote)
            total += lineas
            suma += peso
    return total, suma


# --------------------------------------------------------------------------
# Procesamiento por lotes, en serie y en paralelo
# --------------------------------------------------------------------------


def procesar_lote(lote: list[str]) -> ResumenArchivo:
    """Calcula el resumen de un lote (se ejecuta en hilos o procesos).

    Debe estar a nivel de módulo para poder enviarse a otro proceso.

    >>> r = procesar_lote(["1,2,3.5\\n", "2,3,1.5\\n"])
    >>> r.lineas, r.suma_pesos, r.grados["2"]
    (2, 5.0, 2)
    """
    grados: Counter = Counter()
    suma = 0.0
    for linea in lote:
        origen, destino, peso = linea.split(",")
        grados[origen] += 1
        grados[destino] += 1
        suma += float(peso)
    return ResumenArchivo(len(lote), suma, grados)


def combinar(parciales: Iterable[ResumenArchivo]) -> ResumenArchivo:
    """Une los resúmenes parciales de los lotes en el del archivo completo.

    >>> a = ResumenArchivo(1, 2.0, Counter({"x": 1}))
    >>> b = ResumenArchivo(2, 3.0, Counter({"x": 2, "y": 1}))
    >>> r = combinar([a, b])
    >>> r.lineas, r.suma_pesos, dict(r.grados)
    (3, 5.0, {'x': 3, 'y': 1})
    """
    grados: Counter = Counter()
    suma, lineas = 0.0, 0
    for parcial in parciales:
        grados.update(parcial.grados)  # suma los contadores
        suma += parcial.suma_pesos
        lineas += parcial.lineas
    return ResumenArchivo(lineas, suma, grados)


def mapear_acotado(
    ejecutor: Executor,
    funcion: Callable[[T], object],
    elementos: Iterable[T],
    maximo_pendientes: int,
) -> Iterator:
    """Como ``ejecutor.map`` (mismo orden) pero con a lo sumo N tareas activas.

    ``Executor.map`` consume *todos* los elementos de entrada; con
    un archivo grande eso cargaría todos los lotes en memoria y anularía el
    objetivo del batching. Aquí el archivo se sigue leyendo a medida que los
    trabajadores terminan.

    >>> with ThreadPoolExecutor(2) as ejecutor:
    ...     list(mapear_acotado(ejecutor, abs, [-3, 2, -1], 2))
    [3, 2, 1]
    """
    pendientes: deque = deque()
    for elemento in elementos:
        pendientes.append(ejecutor.submit(funcion, elemento))
        if len(pendientes) >= maximo_pendientes:
            yield pendientes.popleft().result()
    while pendientes:
        yield pendientes.popleft().result()


def _procesar(
    ruta: Path,
    ejecutor: Executor | None,
    tamano_lote: int,
    maximo_pendientes: int,
) -> ResumenArchivo:
    """Lee por lotes y procesa cada uno en ``ejecutor`` (o aquí si es None)."""
    with open(ruta, encoding="utf-8") as archivo:
        lotes = leer_en_lotes(archivo, tamano_lote)
        parciales: Iterable[ResumenArchivo]
        if ejecutor is None:
            parciales = map(procesar_lote, lotes)
        else:
            parciales = mapear_acotado(
                ejecutor, procesar_lote, lotes, maximo_pendientes
            )
        return combinar(parciales)


def procesar_secuencial(
    ruta: Path, tamano_lote: int = TAMANO_LOTE_PARALELO
) -> ResumenArchivo:
    """Procesa los lotes uno tras otro."""
    return _procesar(ruta, None, tamano_lote, 1)


def procesar_con_hilos(
    ruta: Path, trabajadores: int = 4, tamano_lote: int = TAMANO_LOTE_PARALELO
) -> ResumenArchivo:
    """Reparte los lotes entre hilos (el GIL limita las tareas de CPU)."""
    with ThreadPoolExecutor(trabajadores) as ejecutor:
        return _procesar(ruta, ejecutor, tamano_lote, trabajadores * 2)


def procesar_con_procesos(
    ruta: Path, trabajadores: int = 4, tamano_lote: int = TAMANO_LOTE_PARALELO
) -> ResumenArchivo:
    """Reparte los lotes entre procesos (cada lote viaja por pickle)."""
    with ProcessPoolExecutor(trabajadores) as ejecutor:
        return _procesar(ruta, ejecutor, tamano_lote, trabajadores * 2)


# --------------------------------------------------------------------------
# Experimento
# --------------------------------------------------------------------------


def _medir_modos(
    modos: list[tuple[str, Callable[[], T]]], contar: Callable[[T], int]
) -> tuple[list[FilaMedida], list[T]]:
    """Mide cada modo (tiempo y pico de memoria) y calcula la aceleración."""
    medidas = []
    for nombre, funcion in modos:
        tiempo, memoria, resultado = medir_tiempo_y_memoria(funcion)
        medidas.append((nombre, tiempo, memoria, resultado))
    base = medidas[0][1]
    filas = [
        FilaMedida(nombre, tiempo, memoria, contar(resultado), base / tiempo)
        for nombre, tiempo, memoria, resultado in medidas
    ]
    return filas, [resultado for *_, resultado in medidas]


def _iguales(a: ResumenArchivo, b: ResumenArchivo) -> bool:
    """Dos resúmenes coinciden (los floats se comparan con tolerancia)."""
    return (
        a.lineas == b.lineas
        and a.grados == b.grados
        and math.isclose(a.suma_pesos, b.suma_pesos, rel_tol=1e-9)
    )


def _medir_escritura(
    ruta: Path, cantidad_lineas: int, tamano_lote: int
) -> list[FilaMedida]:
    """Compara las tres formas de escribir el archivo de aristas."""

    def lineas() -> Iterator[str]:
        return generar_lineas(cantidad_lineas)

    filas, _ = _medir_modos(
        [
            (
                "Sin buffer (flush por línea)",
                lambda: escribir_sin_buffer(ruta, lineas()),
            ),
            (
                f"Buffer de {tamano_lote} líneas",
                lambda: escribir_con_buffer(ruta, lineas(), tamano_lote),
            ),
            (
                "Todo junto (un solo write)",
                lambda: escribir_todo_junto(ruta, lineas()),
            ),
        ],
        contar=lambda escritas: escritas,
    )
    return filas


def _medir_lectura(
    ruta: Path, tamano_lote: int
) -> tuple[list[FilaMedida], bool]:
    """Compara las formas de leer y verifica que den el mismo resultado."""
    filas, leidos = _medir_modos(
        [
            ("Todo en memoria (read)", lambda: leer_todo(ruta)),
            ("Línea por línea", lambda: leer_linea_a_linea(ruta)),
            (
                f"Lotes de {tamano_lote} líneas",
                lambda: leer_por_lotes(ruta, tamano_lote),
            ),
        ],
        contar=lambda resultado: resultado[0],
    )
    coinciden = all(
        r[0] == leidos[0][0] and math.isclose(r[1], leidos[0][1], rel_tol=1e-9)
        for r in leidos
    )
    return filas, coinciden


def _medir_paralelo(
    ruta: Path, trabajadores: int, lote_paralelo: int
) -> tuple[list[FilaParalelo], bool]:
    """Procesa el archivo en secuencial, con hilos y con procesos."""
    pruebas = (
        ("Secuencial", lambda: procesar_secuencial(ruta, lote_paralelo)),
        (
            f"Hilos ({trabajadores})",
            lambda: procesar_con_hilos(ruta, trabajadores, lote_paralelo),
        ),
        (
            f"Procesos ({trabajadores})",
            lambda: procesar_con_procesos(ruta, trabajadores, lote_paralelo),
        ),
    )
    tiempos: list[float] = []
    resumenes: list[ResumenArchivo] = []
    for _nombre, funcion in pruebas:
        inicio = time.perf_counter()
        resumenes.append(funcion())
        tiempos.append((time.perf_counter() - inicio) * 1000)
    lotes = math.ceil(resumenes[0].lineas / lote_paralelo)
    filas = [
        FilaParalelo(
            nombre, tiempo, lotes, resumen.lineas, tiempos[0] / tiempo
        )
        for (nombre, _), tiempo, resumen in zip(
            pruebas, tiempos, resumenes, strict=True
        )
    ]
    coinciden = all(_iguales(resumenes[0], r) for r in resumenes)
    return filas, coinciden


def ejecutar_entrada_salida(
    cantidad_lineas: int = LINEAS_ARCHIVO,
    tamano_lote: int = TAMANO_LOTE,
    trabajadores: int = 4,
) -> ResultadoEntradaSalida:
    """Escribe, lee y procesa un archivo grande con las distintas técnicas.

    El archivo se crea en una carpeta temporal que se borra al terminar. El
    archivo recién escrito está en la caché del sistema operativo, por lo
    que la lectura es más rápida que con un disco "frío".
    """
    lote_paralelo = max(tamano_lote, TAMANO_LOTE_PARALELO)
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "aristas.csv"
        escritura = _medir_escritura(ruta, cantidad_lineas, tamano_lote)
        tamano_kb = ruta.stat().st_size / BYTES_POR_KB
        lectura, lecturas_coinciden = _medir_lectura(ruta, tamano_lote)
        paralelo, paralelo_coincide = _medir_paralelo(
            ruta, trabajadores, lote_paralelo
        )

    return ResultadoEntradaSalida(
        cantidad_lineas,
        tamano_kb,
        tamano_lote,
        lote_paralelo,
        trabajadores,
        escritura,
        lectura,
        paralelo,
        lecturas_coinciden and paralelo_coincide,
    )
