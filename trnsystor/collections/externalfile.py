"""ExternalFileCollection module."""

import collections

import tabulate
from path import Path

from trnsystor.externalfile import ExternalFile
from trnsystor.utils import standardize_name


class ExternalFileCollection(collections.UserDict):
    """A collection of :class:`ExternalFile` objects."""

    def __getitem__(self, key):
        """Get item."""
        if isinstance(key, int):
            value = list(self.data.values())[key]
        elif isinstance(key, slice):
            value = list(self.data.values()).__getitem__(key)
        else:
            value = super().__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """Set item."""
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
        """Return deck representation of self."""
        return self._to_deck()

    @classmethod
    def from_dict(cls, dictionary):
        """Construct from a dict of :class:`~ExternalFile` objects.

        The object's ``id`` is used as the key.

        Args:
            dictionary (dict): The dict of {key: :class:`~ExternalFile`}
        """
        item = cls()
        for key in dictionary:
            named_key = standardize_name(dictionary[key].question)
            item.__setitem__(named_key, dictionary[key])
        return item

    def _to_deck(self):
        """Return deck representation of self."""
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
