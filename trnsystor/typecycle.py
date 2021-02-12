"""TypeCycle module."""
import collections
import itertools

from bs4 import Tag


class TypeCycle:
    """TypeCycle class."""

    def __init__(
        self,
        role=None,
        firstRow=None,
        lastRow=None,
        cycles=None,
        minSize=None,
        maxSize=None,
        paramName=None,
        question=None,
    ):
        """Initialize object."""
        self.role = role
        self.firstRow = firstRow
        self.lastRow = lastRow
        self.cycles = cycles
        self.minSize = minSize
        self.maxSize = maxSize
        self.paramName = paramName
        self.question = question

    @classmethod
    def from_tag(cls, tag):
        """Create TypeCycle from Tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        dict_ = collections.defaultdict(list)
        for attr in filter(lambda x: isinstance(x, Tag), tag):
            if attr.name != "cycles" and not attr.is_empty_element:
                dict_[attr.name] = attr.text
            elif attr.is_empty_element:
                pass
            else:
                dict_["cycles"].extend(
                    [cls.from_tag(tag) for tag in attr if isinstance(tag, Tag)]
                )
        return cls(**dict_)

    def __repr__(self):
        """Return repr(self)."""
        return self.role + " {} to {}".format(self.firstRow, self.lastRow)

    @property
    def default(self):
        """Return the default value of self."""
        return int(self.minSize)

    @property
    def idxs(self):
        """0-based index of the TypeVariable(s) concerned with this cycle."""
        return (
            list(
                itertools.chain(
                    *(
                        range(int(cycle.firstRow) - 1, int(cycle.lastRow))
                        for cycle in self.cycles
                    )
                )
            )
            if self.cycles
            else None
        )

    @property
    def is_question(self):
        """Return True if self is a question."""
        return (
            any(cycle.question is not None for cycle in self.cycles)
            if self.cycles
            else None
        )
