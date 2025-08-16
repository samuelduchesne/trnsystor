"""Public package interface."""

from __future__ import annotations

from importlib import metadata

from outdated import warn_if_outdated

from .collections import EquationCollection
from .controlcards import ControlCards
from .deck import Deck
from .statement import Equation
from .trnsysmodel import TrnsysModel

__all__ = [
    "Equation",
    "EquationCollection",
    "ControlCards",
    "Deck",
    "TrnsysModel",
    "__version__",
]

try:
    __version__ = metadata.version("trnsystor")
except metadata.PackageNotFoundError:  # pragma: no cover - fallback for local runs
    __version__ = "0.0.0"
else:  # pragma: no branch
    warn_if_outdated("trnsystor", __version__)
