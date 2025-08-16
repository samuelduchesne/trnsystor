"""Trnsystor Module."""

# Version of the package
from pkg_resources import DistributionNotFound, get_distribution

from .collections import EquationCollection
from .controlcards import ControlCards
from .deck import Deck
from .statement import Equation
from .trnsysmodel import TrnsysModel

try:
    __version__ = get_distribution("archetypal").version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0"  # should happen only if package is copied, not installed.
else:
    # warn if a newer version of trnsystor is available
    from outdated import warn_if_outdated
    warn_if_outdated("trnsystor", __version__)

__all__ = [
    "Equation",
    "EquationCollection",
    "ControlCards",
    "Deck",
    "TrnsysModel",
    "__version__",
]
