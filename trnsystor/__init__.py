"""Trnsystor Module."""

from outdated import warn_if_outdated

from .collections import EquationCollection
from .controlcards import ControlCards
from .deck import Deck
from .statement import Equation
from .trnsysmodel import TrnsysModel

# Version of the package
from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution("archetypal").version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0"  # should happen only if package is copied, not installed.
else:
    # warn if a newer version of trnsystor is available
    from outdated import warn_if_outdated

__all__ = [
    "Equation",
    "EquationCollection",
    "ControlCards",
    "Deck",
    "TrnsysModel",
    "__version__",
]
