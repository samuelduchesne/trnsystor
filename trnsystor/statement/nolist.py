"""NoList Statement."""

from trnsystor.statement.statement import Statement


class NoList(Statement):
    """NOLIST Statement.

    The NOLIST statement is used to turn off the listing of the TRNSYS input
    file.
    """

    def __init__(self, active=True):
        """Initialize object.

        Args:
            active (bool): Setting activate to True will add the NOLIST statement
        """
        super().__init__()
        self.active = active
        self.doc = "NOLIST statement"

    def _to_deck(self):
        """Return deck representation of self."""
        return "NOLIST" if self.active else ""
