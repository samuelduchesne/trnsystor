"""End Statement."""
from trnsystor.statement.statement import Statement


class End(Statement):
    """END Statement.

    The END statement must be the last line of a TRNSYS input file. It
    signals the TRNSYS processor that no more control statements follow and that
    the simulation may begin.
    """

    def __init__(self):
        """Initialize object."""
        super().__init__()
        self.doc = "The END Statement"

    def _to_deck(self):
        """Return deck representation of self."""
        return "END"
