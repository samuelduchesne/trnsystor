# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from trnsystor.statement.statement import Statement


class NoList(Statement):
    """The NOLIST statement is used to turn off the listing of the TRNSYS input
    file.
    """

    def __init__(self, active=True):
        """
        Args:
            active (bool): Setting activate to True will add the NOLIST statement
        """
        super().__init__()
        self.active = active
        self.doc = "NOLIST statement"

    def _to_deck(self):
        return "NOLIST" if self.active else ""
