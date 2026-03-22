"""VariableCollection module."""

import collections

from pint import Quantity

from trnsystor.statement import Constant, Equation
from trnsystor.typevariable import TypeVariable
from trnsystor.utils import _parse_value, standardize_name


class VariableCollection(collections.UserDict):
    """A collection of :class:`VariableType` as a dict.

    Handles getting and setting variable values.
    """

    def __getattr__(self, key):
        """Get attribute."""
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super().__getitem__(key)
        return value

    def __getitem__(self, key):
        """Get item."""
        if isinstance(key, int):
            value = list(self.data.values())[key]
        elif isinstance(key, slice):
            value = list(self.data.values()).__getitem__(key)
        else:
            value = super().__getitem__(key)
        return value

    def __setattr__(self, key, value):
        """Set attribute."""
        if isinstance(value, dict):
            super().__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __setitem__(self, key, value):
        """Set item."""
        if isinstance(value, TypeVariable):
            """if a TypeVariable is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, int | float | str):
            """a str, float, int, etc. is passed"""
            existing = (
                self.data[key]
                if isinstance(key, str)
                else list(self.data.values())[key]
            )
            value = _parse_value(
                value, existing.type, existing.unit, (existing.min, existing.max)
            )
            existing.__setattr__("value", value)
        elif isinstance(value, Quantity):
            existing_q = (
                self.data[key]
                if isinstance(key, str)
                else list(self.data.values())[key]
            )
            target_units = (
                existing_q.value.units
                if isinstance(existing_q.value, Quantity)
                else None
            )
            new_val = value.to(target_units) if target_units is not None else value
            existing_q.__setattr__("value", new_val)
        elif isinstance(value, Equation | Constant):
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                f"Cannot set a value of type {type(value)} in this VariableCollection"
            )

    def __str__(self) -> str:
        """Return Deck representation."""
        return self._to_deck()

    def _to_deck(self) -> str:
        """Return deck representation of self."""
        return ""

    @classmethod
    def from_dict(cls, dictionary):
        """Return VariableCollection from dict.

        Sets also the class attribute using ``named_key``.
        """
        item = cls()
        for key in dictionary:
            named_key = standardize_name(dictionary[key].name)
            item.__setitem__(named_key, dictionary[key])
            setattr(item, named_key, dictionary[key])
        return item

    @property
    def size(self):
        """The number of variable in the collection."""
        return len(self)
