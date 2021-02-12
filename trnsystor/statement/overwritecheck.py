"""OverwriteCheck Statement."""

from trnsystor.statement.statement import Statement


class OverwriteCheck(Statement):
    """OverwriteCheck Statement.

    A common error in non standard and user written TRNSYS Type routines is
    to reserve too little space in the global output array. By default, each
    Type is accorded 20 spots in the global TRNSYS output array. However, there
    is no way to prevent the Type from then writing in (for example) the 21st
    spot; the entire global output array is always accessible. By activating the
    OVERWRITE_CHECK statement, the TRNSYS kernel checks to make sure that each
    Type did not write outside its allotted space. As with the NAN_CHECK
    statement, OVERWRITE_CHECK is a time consuming process and should only be
    used as a debugging tool when a simulation is ending in error.
    """

    def __init__(self, n=0):
        """Initialize an OVERWRITE_CHECK object.

        Hint:
            OVERWRITE_CHECK is a time consuming process and should only be used
            as a debugging tool when a simulation is ending in error.

        Args:
            n (int): Is 0 if the OVERWRITE_CHECK feature is not desired or 1 if
                OVERWRITE_CHECK feature is desired.
        """
        super().__init__()
        self.n = int(n)
        self.doc = "The OVERWRITE_CHECK Statement"

    def _to_deck(self):
        """Return deck representation of self."""
        return "OVERWRITE_CHECK {}".format(self.n)
