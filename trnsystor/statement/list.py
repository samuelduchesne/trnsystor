# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from trnsystor.statement.statement import Statement


class List(Statement):
    """The LIST statement is used to turn on the TRNSYS processor listing after
    it has been turned off by a NOLIST statement.
    """

    def __init__(self, activate=False):
        """Hint:
            The listing is assumed to be on at the beginning of a TRNSYS input
            file. As many LIST cards as desired may appear in a TRNSYS input
            file and may be located anywhere in the input file.

        Args:
            activate (bool):
        """
        super().__init__()
        self.activate = activate
        self.doc = "The LIST Statement"
