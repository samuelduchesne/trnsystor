"""SpecialCard module."""
from bs4 import Tag


class SpecialCard(object):
    """SpecialCard class.

    Once the user has defined the Parameters, Inputs, Outputs, and Derivatives,
    some components require addition description statements (or Cards). An example of a
    model that requires a special card is the TYPE 65 Online plotter which must
    specify the titles for each axis and for the plot. These special cards can be
    inserted into the TRNSYS input file by the use of the Special Cards section which
    is also accessed through the Variables Tab of the Proforma.
    """

    def __init__(self, name=None, question=None, default=None, answers=None):
        """Initialize object."""
        if answers is None:
            answers = []
        self.name = name
        self.answers = [answer for answer in answers]
        self.default = default
        self.question = question

    @classmethod
    def from_tag(cls, tag):
        """Create SpecialCard from Tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        name = tag.find("name").text if tag.find("name") else None
        question = tag.find("question").text if tag.find("question") else None
        default = tag.find("answer").text if tag.find("answer") else None
        answers = [
            tag.text for tag in tag.find("answers").children if isinstance(tag, Tag)
        ]
        return cls(name, question, default, answers)
