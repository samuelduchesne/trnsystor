"""Sphinx configuration for trnsystor documentation."""

import os
import sys
from importlib.metadata import version

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("trnsystor"))

# -- Project information -----------------------------------------------------

project = "trnsystor"
copyright = "2019, Samuel Letellier-Duchesne"
author = "Samuel Letellier-Duchesne"

release = version("trnsystor")

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
    "myst_parser",
]

source_suffix = [".rst", ".md"]

templates_path = ["_templates"]


def setup(app):
    app.add_css_file("theme_overrides.css")
    app.add_js_file("copybutton.js")


exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]

autosummary_generate = True
autoclass_content = "both"
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
    "pint": ("https://pint.readthedocs.io/en/stable/", None),
    "sympy": ("https://docs.sympy.org/latest/", None),
}
