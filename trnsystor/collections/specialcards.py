# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import collections

import tabulate

from trnsystor.specialcard import SpecialCard


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
            _ins.append(
                [" ".join(a for a in [special_card.name, special_card.default] if a)]
            )
        core = tabulate.tabulate(_ins, tablefmt="plain")

        return core

    @property
    def size(self):
        """Return length of collection."""
        return len(self)
