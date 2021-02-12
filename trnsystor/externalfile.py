# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import itertools

from bs4 import Tag
from path import Path


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
