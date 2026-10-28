"""ConfiguraciÃ³n de Sphinx."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

project = "Rutas en grafos: BFS, Dijkstra y A*"
author = "Rosales Mercado"
release = "3.0.0"
language = "es"

extensions = [
    "sphinx.ext.autodoc",  # documentaciÃ³n desde los docstrings
    "sphinx.ext.napoleon",  # docstrings estilo Google
    "sphinx.ext.viewcode",  # enlaces al cÃ³digo fuente
    "sphinx.ext.doctest",  # ejecuta los ejemplos >>> de la documentaciÃ³n
]
napoleon_custom_sections = [("Atributos", "params_style")]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
html_theme = "alabaster"
html_static_path = ["_static"]
html_css_files = ["oscuro.css"]
exclude_patterns = ["_build"]
