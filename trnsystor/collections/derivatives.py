# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import tabulate

from trnsystor.collections.variable import VariableCollection
from trnsystor.typevariable import TypeVariable


class DerivativesCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Derivatives"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = "{} Inputs:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Returns the string representation for the Input File (.dck)"""

        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        head = "DERIVATIVES {}\n".format(self.size)
        _ins = []
        derivative: TypeVariable
        for derivative in self.values():
            _ins.append((derivative.value.m, "! {}".format(derivative.name)))
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")

        return head + core + "\n"
