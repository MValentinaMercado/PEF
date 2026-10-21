"""Endpoints del editor: CRUD del grafo y búsqueda de rutas."""

from fastapi import APIRouter, HTTPException

from api.esquemas import (
    AristaEntrada,
    AristaSalida,
    BloqueoEntrada,
    ConsultaEntrada,
    FilaResultado,
    GrafoSalida,
    NodoCambio,
    NodoEntrada,
    NodoSalida,
)
from api.estado import estado
from rutas.algoritmos import ALGORITMOS
from rutas.ejemplo import crear_grafo_ejemplo
from rutas.grafo import Grafo
from rutas.informacion import INFORMACION_ALGORITMOS
from rutas.mediciones import medir_consulta

router = APIRouter(prefix="/api")


def serializar(grafo: Grafo) -> GrafoSalida:
    """Convierte el grafo en la estructura JSON que consume el HTML."""
    nodos = [
        NodoSalida(nombre=n, x=x, y=y)
        for n, (x, y) in grafo.posiciones.items()
    ]
    aristas = [
        AristaSalida(a=a, b=b, peso=peso, bloqueada=grafo.esta_bloqueada(a, b))
        for a, vecinos in grafo.adyacencia.items()
        for b, peso in vecinos.items()
        if a < b
    ]
    return GrafoSalida(version=grafo.version, nodos=nodos, aristas=aristas)


def _exigir_nodo(grafo: Grafo, nombre: str) -> None:
    if nombre not in grafo.adyacencia:
        raise HTTPException(404, f"El nodo '{nombre}' no existe.")


def _exigir_arista(grafo: Grafo, a: str, b: str) -> None:
    _exigir_nodo(grafo, a)
    _exigir_nodo(grafo, b)
    if b not in grafo.adyacencia[a]:
        raise HTTPException(404, f"No existe la conexión {a}–{b}.")


@router.get("/grafo", response_model=GrafoSalida)
def obtener_grafo() -> GrafoSalida:
    """Devuelve el grafo actual."""
    with estado.cerrojo_grafo:
        return serializar(estado.grafo)


@router.post("/grafo/ejemplo", response_model=GrafoSalida)
def cargar_ejemplo() -> GrafoSalida:
    """Reemplaza el grafo por el ejemplo de 6 nodos."""
    with estado.cerrojo_grafo:
        estado.grafo = crear_grafo_ejemplo()
        return serializar(estado.grafo)


@router.delete("/grafo", response_model=GrafoSalida)
def limpiar_grafo() -> GrafoSalida:
    """Elimina todos los nodos y conexiones."""
    with estado.cerrojo_grafo:
        estado.grafo = Grafo()
        return serializar(estado.grafo)


@router.post("/nodos", response_model=GrafoSalida, status_code=201)
def crear_nodo(datos: NodoEntrada) -> GrafoSalida:
    """Crea un nodo; si no trae nombre se asigna el siguiente libre."""
    with estado.cerrojo_grafo:
        grafo = estado.grafo
        nombre = datos.nombre or grafo.nombre_libre()
        if nombre in grafo.adyacencia:
            raise HTTPException(409, f"El nodo '{nombre}' ya existe.")
        grafo.agregar_nodo(nombre, datos.x, datos.y)
        return serializar(grafo)


@router.patch("/nodos/{nombre}", response_model=GrafoSalida)
def editar_nodo(nombre: str, cambio: NodoCambio) -> GrafoSalida:
    """Mueve y/o renombra un nodo."""
    with estado.cerrojo_grafo:
        grafo = estado.grafo
        _exigir_nodo(grafo, nombre)
        x, y = grafo.posiciones[nombre]
        if cambio.x is not None or cambio.y is not None:
            grafo.mover_nodo(
                nombre,
                x if cambio.x is None else cambio.x,
                y if cambio.y is None else cambio.y,
            )
        nuevo = cambio.nuevo_nombre
        if (
            nuevo
            and nuevo != nombre
            and not grafo.renombrar_nodo(nombre, nuevo)
        ):
            raise HTTPException(409, f"El nodo '{nuevo}' ya existe.")
        return serializar(grafo)


@router.delete("/nodos/{nombre}", response_model=GrafoSalida)
def eliminar_nodo(nombre: str) -> GrafoSalida:
    """Elimina un nodo y todas sus conexiones."""
    with estado.cerrojo_grafo:
        _exigir_nodo(estado.grafo, nombre)
        estado.grafo.eliminar_nodo(nombre)
        return serializar(estado.grafo)


@router.put("/aristas", response_model=GrafoSalida)
def guardar_arista(datos: AristaEntrada) -> GrafoSalida:
    """Crea o actualiza la conexión (y su peso) entre dos nodos."""
    with estado.cerrojo_grafo:
        grafo = estado.grafo
        _exigir_nodo(grafo, datos.a)
        _exigir_nodo(grafo, datos.b)
        if datos.a == datos.b:
            raise HTTPException(
                422, "No se permite conectar un nodo consigo mismo."
            )
        grafo.conectar(datos.a, datos.b, datos.peso)
        return serializar(grafo)


@router.patch("/aristas/bloqueo", response_model=GrafoSalida)
def bloquear_arista(datos: BloqueoEntrada) -> GrafoSalida:
    """Bloquea o habilita una conexión para simular cortes."""
    with estado.cerrojo_grafo:
        _exigir_arista(estado.grafo, datos.a, datos.b)
        estado.grafo.establecer_bloqueo(datos.a, datos.b, datos.bloqueada)
        return serializar(estado.grafo)


@router.delete("/aristas/{a}/{b}", response_model=GrafoSalida)
def eliminar_arista(a: str, b: str) -> GrafoSalida:
    """Elimina la conexión entre ``a`` y ``b``."""
    with estado.cerrojo_grafo:
        _exigir_arista(estado.grafo, a, b)
        estado.grafo.eliminar_arista(a, b)
        return serializar(estado.grafo)


@router.post("/rutas", response_model=list[FilaResultado])
def buscar_rutas(consulta: ConsultaEntrada) -> list[FilaResultado]:
    """Ejecuta y mide (tiempo y memoria reales) los algoritmos pedidos."""
    desconocidos = [n for n in consulta.algoritmos if n not in ALGORITMOS]
    if desconocidos:
        raise HTTPException(422, f"Algoritmo desconocido: {desconocidos}")
    if consulta.origen == consulta.destino:
        raise HTTPException(422, "Origen y destino deben ser distintos.")
    with estado.cerrojo_grafo:
        grafo = estado.grafo
        _exigir_nodo(grafo, consulta.origen)
        _exigir_nodo(grafo, consulta.destino)
        grafo.factor_heuristica()  # se calcula antes de medir A*
        filas = []
        with estado.cerrojo_medicion:
            for nombre in consulta.algoritmos:
                medida = medir_consulta(
                    ALGORITMOS[nombre],
                    grafo,
                    consulta.origen,
                    consulta.destino,
                    consulta.repeticiones,
                )
                filas.append(
                    FilaResultado(
                        algoritmo=nombre,
                        ruta=medida.ruta,
                        distancia=(medida.distancia if medida.ruta else None),
                        tiempo_ms=medida.tiempo_ms,
                        memoria_kb=medida.memoria_kb,
                        nodos_explorados=medida.nodos_explorados,
                    )
                )
        return filas


@router.get("/informacion")
def informacion_algoritmos() -> list:
    """Tabla informativa de funcionamiento y complejidades."""
    return [fila._asdict() for fila in INFORMACION_ALGORITMOS]
