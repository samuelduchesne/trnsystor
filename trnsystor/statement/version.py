# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from trnsystor.statement.statement import Statement


class Version(Statement):
    """Added with TRNSYS version 15. The idea of the command is that by labeling
    decks with the TRNSYS version number that they were created under, it is
    easy to keep TRNSYS backwards compatible. The version number is saved by the
    TRNSYS kernel and can be acted upon.
    """

    def __init__(self, v=(18, 0)):
        """Initialize the Version statement

        Args:
            v (tuple): A tuple of (major, minor) eg. 18.0 :> (18, 0)
        """
        super().__init__()
        self.v = v
        self.doc = "The VERSION Statement"

    @classmethod
    def from_string(cls, string):
        """
        Args:
            string:
        """
        return cls(tuple(map(int, string.split("."))))

    def _to_deck(self):
        return "VERSION {}".format(".".join(map(str, self.v)))
