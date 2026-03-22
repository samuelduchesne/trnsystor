"""NoCheck Statement."""

from trnsystor.statement.statement import Statement


class NoCheck(Statement):
    """NoCheck Statement.

    TRNSYS allows up to 20 different INPUTS to be removed from the list of
    INPUTS to be checked for convergence (see Section 1.9).
    """

    def __init__(self, inputs=None):
        """Initialize object.

        Args:
            inputs (list of Input): The list of Inputs.
        """
        super().__init__()
        if not inputs:
            inputs = []
        if len(inputs) > 20:
            raise ValueError(
                "TRNSYS allows only up to 20 different INPUTS to be removed"
            )
        self.inputs = inputs
        self.doc = "CHECK Statement"

    def _to_deck(self):
        """Return deck representation of self."""
        from trnsystor.serialization.statements import serialize_nocheck

        return serialize_nocheck(self)
