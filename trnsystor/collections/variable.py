"""VariableCollection module."""
import collections

from pint.quantity import _Quantity

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
            value = super(VariableCollection, self).__getitem__(key)
        return value

    def __getitem__(self, key):
        """Get item."""
        if isinstance(key, int):
            value = list(self.data.values())[key]
        elif isinstance(key, slice):
            value = list(self.data.values()).__getitem__(key)
        else:
            value = super(VariableCollection, self).__getitem__(key)
        return value

    def __setattr__(self, key, value):
        """Set attribute."""
        if isinstance(value, dict):
            super(VariableCollection, self).__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __setitem__(self, key, value):
        """Set item."""
        if isinstance(value, TypeVariable):
            """if a TypeVariable is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, (int, float, str)):
            """a str, float, int, etc. is passed"""
            value = _parse_value(
                value, self[key].type, self[key].unit, (self[key].min, self[key].max)
            )
            self[key].__setattr__("value", value)
        elif isinstance(value, _Quantity):
            self[key].__setattr__("value", value.to(self[key].value.units))
        elif isinstance(value, (Equation, Constant)):
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                "Cannot set a value of type {} in this "
                "VariableCollection".format(type(value))
            )

    def __str__(self):
        """Return Deck representation."""
        return self._to_deck()

    def _to_deck(self):
        """Return deck representation of self."""
        pass

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
