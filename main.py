"""Punto de entrada: levanta el servidor FastAPI con uvicorn.

Ejecutar con ``python main.py`` y abrir http://127.0.0.1:8000
"""

import uvicorn


def main() -> None:
    """Arranca el servidor web."""
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
