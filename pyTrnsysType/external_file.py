# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and pyTrnsysType contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import collections
import itertools

import tabulate
from bs4 import Tag
from path import Path

from pyTrnsysType import standerdized_name


class ExternalFile(object):
    """ExternalFile class."""

    logic_unit = itertools.count(start=30)
    _logic_unit = itertools.count(start=30)

    def __init__(self, question, default, answers, parameter, designate):
        """Initilize object from arguments.

        Args:
            question (str):
            default (str):
            answers (list of str):
            parameter (str):
            designate (bool): If True, the external files are assigned to
                logical unit numbers from within the TRNSYS input file. Files
                that are assigned to a logical unit number using a DESIGNATE
                statement will not be opened by the TRNSYS kernel.
        """
        self.designate = designate
        self.parameter = parameter
        self.answers = [Path(answer) for answer in answers]
        self.default = Path(default)
        self.question = question

        self.logical_unit = next(self._logic_unit)

        self.value = self.default

    @classmethod
    def from_tag(cls, tag):
        """
        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        question = tag.find("question").text
        default = tag.find("answer").text
        answers = [
            tag.text for tag in tag.find("answers").children if isinstance(tag, Tag)
        ]
        parameter = tag.find("parameter").text
        designate = tag.find("designate").text
        return cls(question, default, answers, parameter, designate)


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
