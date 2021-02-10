# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and pyTrnsysType contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import collections

from pint.quantity import _Quantity

from pyTrnsysType import standerdized_name
from pyTrnsysType.statement import Equation, Constant
from pyTrnsysType.typevariable import TypeVariable
from pyTrnsysType.utils import _parse_value


class VariableCollection(collections.UserDict):
    """A collection of :class:`VariableType` as a dict. Handles getting and
    setting variable values.
    """

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super(VariableCollection, self).__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """
        Args:
            key:
            value:
        """

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
        return self._to_deck()

    def _to_deck(self):
        pass

    @classmethod
    def from_dict(cls, dictionary):
        """
        Args:
            dictionary:
        """
        item = cls()
        for key in dictionary:
            named_key = standerdized_name(dictionary[key].name)
            item.__setitem__(named_key, dictionary[key])
            setattr(item, named_key, dictionary[key])
        return item

    @property
    def size(self):
        """The number of parameters"""
        return len(self)
