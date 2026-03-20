"""Trnsystor - A python TRNSYS type parser."""

from importlib.metadata import PackageNotFoundError, version

from .collections import EquationCollection
from .controlcards import ControlCards
from .deck import Deck
from .statement import Equation
from .trnsysmodel import TrnsysModel

try:
    __version__ = version("trnsystor")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "ControlCards",
    "Deck",
    "Equation",
    "EquationCollection",
    "TrnsysModel",
    "__version__",
]
