# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from trnsystor.statement.statement import Statement


class Map(Statement):
    """The MAP statement is an optional control statement that is used to obtain
    a component output map listing which is particularly useful in debugging
    component interconnections.
    """

    def __init__(self, activate=True):
        """Setting active to True will add the MAP statement

        Args:
            activate (bool): Setting active to True will add the MAP statement
        """
        super().__init__()
        self.active = activate
        self.doc = "MAP statement"

    def _to_deck(self):
        return "MAP" if self.active else ""
