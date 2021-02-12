"""NaNCheck Statement."""

from trnsystor.statement.statement import Statement


class NaNCheck(Statement):
    """NaNCheck Statement.

    One problem that has plagued TRNSYS simulation debuggers is that in
    Fortran, the “Not a Number” (NaN) condition can be passed along through
    numerous subroutines without being flagged as an error. For example, a
    division by zero results in a variable being set to NaN. This NaN can then
    be used in subsequent equation, causing them to be set to NaN as well. The
    problem persists for a time until a Range Check or an Integer Overflow error
    occurs and actually stops simulation progress. To alleviate the problem, the
    NAN_CHECK Statement was added as an optional debugging feature in TRNSYS
    input files.
    """

    def __init__(self, n=0):
        """Initialize a NaNCheck object.

        Hint:
            If the NAN_CHECK statement is present (n=1), then the TRNSYS kernel
            checks every output of each component at each iteration and
            generates a clean error if ever one of those outputs has been set to
            the FORTRAN NaN condition. Because this checking is very time
            consuming, users are not advised to leave NAN_CHECK set in their
            input files as it causes simulations to run much more slowly.

        Args:
            n (int): Is 0 if the NAN_CHECK feature is not desired or 1 if
                NAN_CHECK feature is desired. Default is 0.
        """
        super().__init__()
        self.n = int(n)
        self.doc = "The NAN_CHECK Statement"

    def _to_deck(self):
        """Return deck representation of self."""
        return "NAN_CHECK {}".format(self.n)
