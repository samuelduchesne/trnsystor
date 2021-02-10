# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and pyTrnsysType contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import collections

import tabulate

from pyTrnsysType.specialcard import SpecialCard


class SpecialCardsCollection(collections.UserList):
    """Subclass of :class:`VariableCollection` specific to Derivatives."""

    def __repr__(self):
        """Return repr."""
        return self._to_deck()

    def __str__(self):
        """Return string."""
        return self._to_deck()

    def _to_deck(self):
        """Return the deck representation for the SpecialCards (.dck)."""

        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        _ins = []
        special_card: SpecialCard
        for special_card in self:
            _ins.append((special_card.name, special_card.default))
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")

        return core + "\n"

    @property
    def size(self):
        """Return length of collection."""
        return len(self)
