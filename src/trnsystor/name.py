"""Name module."""

from __future__ import annotations

from typing import ClassVar


class Name:
    """Name class.

    Handles the attribution of user defined names for :class:`TrnsysModel`,
    :class:`EquationCollection` and more.
    """

    existing: ClassVar[set[str]] = set()  # default registry for standalone usage

    def __init__(self, name=None, registry=None):
        """Pick a name. Will increment the name if already used.

        Args:
            name (str): The desired name.
            registry (set, optional): A set of existing names to check
                against. Defaults to the class-level ``existing`` set.
        """
        self._registry = registry if registry is not None else self.existing
        self.name = self.create_unique(name)

    def create_unique(self, name):
        """Return unique name.

        Checks if ``name`` has already been used. If so, try to increment until not
        used.

        Args:
            name (str): The name to render unique.
        """
        if not name:
            return None
        base = name.split("_")[0]
        key = name
        i = 0
        while key in self._registry:
            i += 1
            key = f"{base}_{i}"
        self._registry.add(key)
        return key

    def __repr__(self):
        """Return str(self)."""
        return str(self)

    def __str__(self):
        """Return str(self)."""
        return str(self.name)
