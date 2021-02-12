"""TimeReport Statement."""

from trnsystor.statement.statement import Statement


class TimeReport(Statement):
    """TIME_REPORT Statement.

    The statement TIME_REPORT turns on or off the internal calculation of the
    time spent on each unit. If this feature is desired, the listing file will
    contain this information at the end of the file.
    """

    def __init__(self, n=0):
        """Initialize a TIME_REPORT object.

        Args:
            n (int): Is 0 if the TIME_REPORT feature is not desired or 1 if
                TIME_REPORT feature is desired.
        """
        super().__init__()
        self.n = n
        self.doc = "The TIME_REPORT Statement"

    def _to_deck(self):
        """Return deck representation of self."""
        return "TIME_REPORT {n}".format(n=self.n)
