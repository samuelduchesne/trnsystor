"""Docs module."""
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

from trnsystor import __version__

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("trnsystor"))

# -- Project information -----------------------------------------------------

project = "trnsystor"
copyright = "2019, Samuel Letellier-Duchesne"
author = "Samuel Letellier-Duchesne"

# The full version, including alpha/beta/rc tags

version = release = __version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
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
    "sphinx.ext.autosummary",
    "recommonmark",
]

source_suffix = [".rst", ".md"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]


def setup(app):
    app.add_stylesheet("theme_overrides.css")
    # app.connect("autodoc-skip-member", skip)
    app.add_javascript("copybutton.js")
    # Add the 'copybutton' javascript, to hide/show the prompt in code examples


def skip(app, what, name, obj, would_skip, options):
    if name == "__init__":
        return False
    return would_skip


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

autosummary_generate = True
autoclass_content = "both"
autodoc_member_order = "bysource"

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("http://pandas.pydata.org/pandas-docs/stable/", None),
    "numpy": ("https://docs.scipy.org/doc/numpy/", None),
    "networkx": (
        "https://networkx.github.io/documentation/stable" "/index" ".html",
        "https://networkx.github.io/objects.inv",
    ),
    "pint": ("https://pint.readthedocs.io/en/0.9/", None),
    "path": ("https://pathpy.readthedocs.io/en/stable/", None),
    "sympy": ("https://docs.sympy.org/latest/", None),
}
