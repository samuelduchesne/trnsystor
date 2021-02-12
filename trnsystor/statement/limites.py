"""Limits Statement."""
from trnsystor.statement.statement import Statement


class Limits(Statement):
    """LIMITS Statement.

    The LIMITS statement is an optional control statement used to set limits
    on the number of iterations that will be performed by TRNSYS during a time
    step before it is determined that the differential equations and/or
    algebraic equations are not converging.
    """

    def __init__(self, m=25, n=10, p=None):
        """Initialize object.

        Args:
            m (int): is the maximum number of iterations which can be performed
                during a time-step before a WARNING message is printed out.
            n (int): is the maximum number of WARNING messages which may be
                printed before the simulation terminates in ERROR.
            p (int, optional): is an optional limit. If any component is called
                p times in one time step, then the component will be traced (See
                Section 2.3.5) for all subsequent calls in the timestep. When p
                is not specified by the user, TRNSYS sets p equal to m.
        """
        super().__init__()
        self.m = m
        self.n = n
        self.p = p if p is not None else self.m
        self.doc = "Max iterations\tMax warnings\tTrace limit"

    def _to_deck(self):
        """Return deck representation of self.

        Examples:
            TOLERANCES 0.001 0.001
        """
        head = "LIMITS {} {} {}".format(self.m, self.n, self.p)
        return str(head)
