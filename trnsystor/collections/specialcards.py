"""SpecialCardsCollection module."""

import collections


class SpecialCardsCollection(collections.UserList):
    """Subclass of :class:`VariableCollection` specific to Derivatives."""

    def __repr__(self):
        """Return repr(self)."""
        return self._to_deck()

    def __str__(self):
        """Return string."""
        return self._to_deck()

    def _to_deck(self):
        """Return deck representation of self."""
        from trnsystor.serialization.variables import serialize_special_cards

        return serialize_special_cards(self)

    @property
    def size(self):
        """Return length of collection."""
        return len(self)
