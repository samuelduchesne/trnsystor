"""List Statement."""
from trnsystor.statement.statement import Statement


class List(Statement):
    """LIST Statement.

    The LIST statement is used to turn on the TRNSYS processor listing after
    it has been turned off by a NOLIST Statement.
    """

    def __init__(self, activate=False):
        """Initialize object.

        Hint:
            The listing is assumed to be on at the beginning of a TRNSYS input
            file. As many LIST cards as desired may appear in a TRNSYS input
            file and may be located anywhere in the input file.

        Args:
            activate (bool): Print to deck if True.
        """
        super().__init__()
        self.activate = activate
        self.doc = "The LIST Statement"
