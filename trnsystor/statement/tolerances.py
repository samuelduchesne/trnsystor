"""Tolerances Statement."""

from trnsystor.statement.statement import Statement


class Tolerances(Statement):
    """TOLERANCES Statement.

    The TOLERANCES statement is an optional control statement used to specify
    the error tolerances to be used during a TRNSYS simulation.
    """

    def __init__(self, epsilon_d=0.01, epsilon_a=0.01):
        """Initialize object.

        Args:
            epsilon_d: is a relative (and -epsilon_d is an absolute) error
                tolerance controlling the integration error.
            epsilon_a: is a relative (and -epsilon_a is an absolute) error
                tolerance controlling the convergence of input and output
                variables.
        """
        super().__init__()
        self.epsilon_d = epsilon_d
        self.epsilon_a = epsilon_a
        self.doc = "Integration\tConvergence"

    def _to_deck(self):
        """Return deck representation of self.

        Examples:
            TOLERANCES 0.001 0.001
        """
        head = "TOLERANCES {} {}".format(self.epsilon_d, self.epsilon_a)
        return str(head)
