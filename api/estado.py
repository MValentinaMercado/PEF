"""Estado compartido de la aplicación: el grafo y un cerrojo de medición."""

import threading

from rutas.ejemplo import crear_grafo_ejemplo
from rutas.grafo import Grafo
from rutas.prediccion import ModeloTiempos


class Estado:
    """Guarda el grafo del editor en memoria (un solo grafo por servidor).

    ``cerrojo_grafo`` evita que dos peticiones modifiquen el grafo a la
    vez. ``cerrojo_medicion`` serializa las mediciones: ``tracemalloc`` es
    global al proceso y dos mediciones simultáneas se falsearían.
    """

    def __init__(self) -> None:
        self.grafo: Grafo = crear_grafo_ejemplo()
        self.cerrojo_grafo = threading.RLock()
        self.cerrojo_medicion = threading.Lock()
        # Se llena al entrenar la regresión de tiempos (ventana Análisis).
        self.modelo: ModeloTiempos | None = None


estado = Estado()
