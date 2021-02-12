"""DFQ Statement."""
from trnsystor.statement.statement import Statement


class DFQ(Statement):
    """DFQ Statement.

    The optional DFQ card allows the user to select one of three algorithms
    built into TRNSYS to numerically solve differential equations (see Manual
    08-Programmer’s Guide for additional information about solution of
    differential equations).
    """

    def __init__(self, k=1):
        """Initialize the Differential Equation Solving Method Statement.

        Args:
            k (int, optional): an integer between 1 and 3. If a DFQ card is not
                present in the TRNSYS input file, DFQ 1 is assumed.

        Note:
            The three numerical integration algorithms are:

            1. Modified-Euler method (a 2nd order Runge-Kutta method)
            2. Non-self-starting Heun's method (a 2nd order Predictor-Corrector
               method)
            3. Fourth-order Adams method (a 4th order Predictor-Corrector
               method)
        """
        super().__init__()
        self.k = k
        self.doc = "TRNSYS numerical integration solver method"

    def _to_deck(self):
        """Return deck representation of self."""
        return str("DFQ {}".format(self.k))
