"""Modelos pydantic de entrada y salida de la API."""

import re

from pydantic import BaseModel, Field, field_validator

PATRON_NOMBRE = re.compile(r"^[A-Za-z0-9_-]{1,12}$")


def validar_nombre(valor: str) -> str:
    """Los nombres son cortos y sin símbolos (van dentro de la URL)."""
    if not PATRON_NOMBRE.match(valor):
        raise ValueError(
            "Nombre inválido: use 1 a 12 letras, números, '_' o '-'."
        )
    return valor


class NodoEntrada(BaseModel):
    """Datos para crear un nodo (el nombre es opcional)."""

    nombre: str | None = None
    x: float = Field(ge=0, le=5000)
    y: float = Field(ge=0, le=5000)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, valor: str | None) -> str | None:
        return None if valor is None else validar_nombre(valor)


class NodoCambio(BaseModel):
    """Cambios parciales de un nodo: posición y/o nombre."""

    x: float | None = Field(default=None, ge=0, le=5000)
    y: float | None = Field(default=None, ge=0, le=5000)
    nuevo_nombre: str | None = None

    @field_validator("nuevo_nombre")
    @classmethod
    def _nombre(cls, valor: str | None) -> str | None:
        return None if valor is None else validar_nombre(valor)


class AristaEntrada(BaseModel):
    """Conexión entre dos nodos con su peso (> 0)."""

    a: str
    b: str
    peso: float = Field(gt=0, le=1e9)


class BloqueoEntrada(BaseModel):
    """Bloquea o habilita una conexión."""

    a: str
    b: str
    bloqueada: bool


class ConsultaEntrada(BaseModel):
    """Origen, destino y algoritmos a ejecutar."""

    origen: str
    destino: str
    algoritmos: list[str] = Field(
        default_factory=lambda: ["BFS", "Dijkstra", "A*"]
    )
    repeticiones: int = Field(default=50, ge=1, le=500)


class NodoSalida(BaseModel):
    """Nodo con su posición."""

    nombre: str
    x: float
    y: float


class AristaSalida(BaseModel):
    """Arista con su peso y estado."""

    a: str
    b: str
    peso: float
    bloqueada: bool


class GrafoSalida(BaseModel):
    """Estado completo del grafo."""

    version: int
    nodos: list[NodoSalida]
    aristas: list[AristaSalida]


class FilaResultado(BaseModel):
    """Fila de la tabla de resultados del editor."""

    algoritmo: str
    ruta: list[str] | None
    distancia: float | None  # None = sin ruta (infinito)
    tiempo_ms: float
    memoria_kb: float
    nodos_explorados: int
