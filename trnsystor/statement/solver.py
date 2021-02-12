"""Solver Statement."""

from trnsystor.statement.statement import Statement


class Solver(Statement):
    """SOLVER Statement.

    A SOLVER command has been added to TRNSYS to select the computational
    scheme. The optional SOLVER card allows the user to select one of two
    algorithms built into TRNSYS to numerically solve the system of algebraic
    and differential equations.
    """

    def __init__(self, k=0, rf_min=1, rf_max=1):
        """Initialize object.

        Args:
            k (int): the solution algorithm.
            rf_min (float): the minimum relaxation factor.
            rf_max (float): the maximum relaxation factor.

        Note:
            k is either the integer 0 or 1. If a SOLVER card is not present in
            the TRNSYS input file, SOLVER 0 is assumed. If k = 0, the SOLVER
            statement takes two additional parameters, RFmin and RFmax:

            The two solution algorithms (k) are:
                * 0: Successive Substitution
                * 1: Powell’s Method
        """
        super().__init__()
        self.rf_max = rf_max
        self.rf_min = rf_min
        self.k = k
        self.doc = (
            "Solver statement\tMinimum relaxation factor\tMaximum " "relaxation factor"
        )

    def _to_deck(self):
        """Return deck representation of self."""
        return (
            "SOLVER {} {} {}".format(self.k, self.rf_min, self.rf_max)
            if self.k == 0
            else "SOLVER {}".format(self.k)
        )
