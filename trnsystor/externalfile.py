"""ExternalFile module."""
import itertools

from bs4 import Tag
from path import Path


class ExternalFile(object):
    """ExternalFile class.

    The External File Specification allows the user to associate a TRNSYS parameter (
    typically a logical unit) with an external file through the use of the TRNSYS
    ASSIGN, FILES, or DESIGNATE statements. This feature allows the author to
    describe a question that will be asked in the assembly window. If the ASSIGN
    statement is used, a parameter has to be associated with this external file to
    define its FORTRAN logical unit number. For example, "Which file contains the
    meteorological information?” When the input file is generated, it will contain a
    TRNSYS ASSIGN statement with the answer to the question and the value of the
    associated parameter. If the user would instead rather use the DESIGNATE input
    file keyword for their component (please see more information in the TRNEdit
    manual), the “Designate” checkbox will have to be clicked.
    """

    logic_unit = itertools.count(start=30)
    _logic_unit = itertools.count(start=30)

    def __init__(self, question, default, answers, parameter, designate):
        """Initialize object from arguments.

        Args:
            question (str): Question to ask.
            default (str): Default answer.
            answers (list of str): List of possible answers.
            parameter (str): The parameter associated with the external file.
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
        """Create ExternalFile from Tag.

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
