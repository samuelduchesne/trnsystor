"""VariableCollection module."""

import collections

from trnsystor.quantity import Quantity
from trnsystor.statement import Constant, Equation
from trnsystor.typevariable import TypeVariable
from trnsystor.utils import _parse_value, standardize_name


class VariableCollection(collections.UserDict):
    """A collection of :class:`VariableType` as a dict.

    Handles getting and setting variable values.
    """

    def __getattr__(self, key):
        """Get attribute."""
        if key.startswith("_"):
            raise AttributeError(key)
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
            self._invalidate_model_cache(existing)
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
            self._invalidate_model_cache(existing_q)
        elif isinstance(value, Equation | Constant):
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                f"Cannot set a value of type {type(value)} in this VariableCollection"
            )

    @staticmethod
    def _invalidate_model_cache(var):
        """Invalidate the parent model's property cache after a value change."""
        if (
            hasattr(var, "model")
            and var.model is not None
            and hasattr(var.model, "_invalidate_cache")
        ):
            var.model._invalidate_cache()

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
        Precomputes ``_idx`` on each variable for O(1) index lookups.
        """
        item = cls()
        for idx, key in enumerate(dictionary):
            var = dictionary[key]
            var._idx = idx  # precompute index
            named_key = standardize_name(var.name)
            item.__setitem__(named_key, var)
            setattr(item, named_key, var)
        return item

    @property
    def size(self):
        """The number of variable in the collection."""
        return len(self)
