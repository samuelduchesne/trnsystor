# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and pytrnsys contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from pytrnsys.statement.statement import Statement


class NoCheck(Statement):
    """TRNSYS allows up to 20 different INPUTS to be removed from the list of
    INPUTS to be checked for convergence (see Section 1.9).
    """

    def __init__(self, inputs=None):
        """
        Args:
            inputs (list of Input):
        """
        super().__init__()
        if not inputs:
            inputs = []
        if len(inputs) > 20:
            raise ValueError(
                "TRNSYS allows only up to 20 different INPUTS to " "be removed"
            )
        self.inputs = inputs
        self.doc = "CHECK Statement"

    def _to_deck(self):
        head = "NOCHECK {}\n".format(len(self.inputs))
        core = "\t".join(
            [
                "{}, {}".format(input.model.unit_number, input.one_based_idx)
                for input in self.inputs
            ]
        )
        return str(head) + str(core)
