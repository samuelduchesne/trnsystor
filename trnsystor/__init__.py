"""Trnsystor Module."""

try:
    from outdated import warn_if_outdated
except Exception:  # pragma: no cover - optional dependency
    def warn_if_outdated(*args, **kwargs):  # type: ignore
        """Fallback when the ``outdated`` package is not available."""
        return None

from .collections import EquationCollection
from .controlcards import ControlCards
from .deck import Deck
from .statement import Equation
from .trnsysmodel import TrnsysModel
from .canvas import StudioCanvas

# Version of the package
from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution("archetypal").version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0"  # should happen only if package is copied, not installed.
else:
    # warn if a newer version of trnsystor is available
    warn_if_outdated("trnsystor", __version__)

__all__ = [
    "Equation",
    "EquationCollection",
    "ControlCards",
    "Deck",
    "TrnsysModel",
    "StudioCanvas",
    "__version__",
]
