"""Trnsystor Module."""

from outdated import warn_if_outdated

from .controlcards import ControlCards
from .deck import Deck
from .trnsysmodel import TrnsysModel

# Version of the package
__version__ = "1.3.2"

# warn if a newer version of archetypal is available
warn_if_outdated("trnsystor", __version__)

__all__ = ["ControlCards", "Deck", "TrnsysModel", "__version__"]
