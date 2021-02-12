"""EqSolver Statement."""
from trnsystor.statement.statement import Statement


class EqSolver(Statement):
    """EqSolver Statement.

    With the release of TRNSYS 16, new methods for solving blocks of
    EQUATIONS statements were added. For additional information on EQUATIONS
    statements, please refer to section 6.3.9. The order in which blocks of
    EQUATIONS are solved is controlled by the EQSOLVER Statement.
    """

    def __init__(self, n=0):
        """Initialize object.

        Hint:
            :attr:`n` can have any of the following values:

            1. n=0 (default if no value is provided) if a component output or
               TIME changes, update the block of equations that depend upon
               those values. Then update components that depend upon the first
               block of equations. Continue looping until all equations have
               been updated appropriately. This equation blocking method is most
               like the method used in TRNSYS version 15 and before.
            2. n=1 if a component output or TIME changes by more than the value
               set in the TOLERANCES Statement (see Section 6.3.3), update the
               block of equations that depend upon those values. Then update
               components that depend upon the first block of equations.
               Continue looping until all equations have been updated
               appropriately.
            3. n=2 treat equations as a component and update them only after
               updating all components.

        Args:
            n (int): The order in which the equations are solved.
        """
        super().__init__()
        self.n = n
        self.doc = "EQUATION SOLVER statement"

    def _to_deck(self):
        """Return deck representation of self."""
        return "EQSOLVER {}".format(self.n)
