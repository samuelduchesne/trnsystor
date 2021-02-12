# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import collections

import tabulate
from path import Path

from trnsystor import standerdized_name
from trnsystor.externalfile import ExternalFile


class ExternalFileCollection(collections.UserDict):
    """A collection of :class:`ExternalFile` objects"""

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super().__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """
        Args:
            key:
            value:
        """
        if isinstance(value, ExternalFile):
            """if a ExternalFile is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, (str, Path)):
            """a str, or :class:Path is passed"""
            value = Path(value)
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                "Cannot set a value of type {} in this "
                "ExternalFileCollection".format(type(value))
            )

    def __str__(self):
        return self._to_deck()

    @classmethod
    def from_dict(cls, dictionary):
        """Construct an :class:`~ExternalFileCollection` from a dict of
        :class:`~ExternalFile` objects with the object's id as a key.

        Args:
            dictionary (dict): The dict of {key: :class:`~ExternalFile`}
        """
        item = cls()
        for key in dictionary:
            # self.parameters[key] = ex_file.logical_unit
            named_key = standerdized_name(dictionary[key].question)
            item.__setitem__(named_key, dictionary[key])
        return item

    def _to_deck(self):
        """Returns the string representation for the external files (.dck)"""
        if self:
            head = "*** External files\n"
            v_ = (
                ("ASSIGN", '"{}"'.format(ext_file.value), ext_file.logical_unit)
                for ext_file in self.values()
            )
            core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")

            return str(head) + str(core)
        else:
            return ""
