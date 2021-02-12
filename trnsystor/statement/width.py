"""Width Statement."""

from trnsystor.statement.statement import Statement


class Width(Statement):
    """WIDTH Statement.

    The WIDTH statement is an optional control statement is used to set the
    number of characters to be allowed on a line of TRNSYS output.

    Note:
        This statement is obsolete.
    """

    def __init__(self, n=120):
        """Initialize the Width Statement.

        Args:
            n (int, optional): n is the number of characters per printed line; n
                must be between 72 and 132.
        """
        super().__init__()
        self.k = self._check_range(int(n))
        self.doc = "The number of printed characters per line"

    def _to_deck(self):
        """Return deck representation of self."""
        return str("WIDTH {}".format(self.k))

    @staticmethod
    def _check_range(n):
        if n >= 72 and n <= 132:
            return n
        else:
            raise ValueError("The Width Statement mus be between 72 and 132.")
