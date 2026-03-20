"""SpecialCardsCollection module."""

import collections

import tabulate


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
        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        _ins = [[" ".join(a for a in [sc.name, sc.default] if a)] for sc in self]
        core = tabulate.tabulate(_ins, tablefmt="plain")

        return core

    @property
    def size(self):
        """Return length of collection."""
        return len(self)
