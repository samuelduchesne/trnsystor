# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import tabulate

from trnsystor.collections.variable import VariableCollection
from trnsystor.statement import Equation, Constant
from trnsystor.typevariable import TypeVariable


class InputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Inputs"""

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

        head = "INPUTS {}\n".format(self.size)
        # "{u_i}, {o_i}": is an integer number referencing the number of the
        # UNIT to which the ith INPUT is connected. is an integer number
        # indicating to which OUTPUT (i.e., the 1st, 2nd, etc.) of UNIT
        # number ui the ith INPUT is connected.
        _ins = []
        for input in self.values():
            if input.is_connected:
                if isinstance(input.predecessor, TypeVariable):
                    _ins.append(
                        (
                            "{},{}".format(
                                input.predecessor.model.unit_number,
                                input.predecessor.one_based_idx,
                            ),
                            "! {out_model_name}:{output_name} -> {in_model_name}:{"
                            "input_name}".format(
                                out_model_name=input.predecessor.model.name,
                                output_name=input.predecessor.name,
                                in_model_name=input.model.name,
                                input_name=input.name,
                            ),
                        )
                    )
                elif isinstance(input.predecessor, (Equation, Constant)):
                    _ins.append(
                        (
                            input.predecessor.name,
                            "! {out_model_name}:{output_name} -> {in_model_name}:{"
                            "input_name}".format(
                                out_model_name=input.predecessor.model.name,
                                output_name=input.predecessor.name,
                                in_model_name=input.model.name,
                                input_name=input.name,
                            ),
                        )
                    )
                else:
                    raise NotImplementedError(
                        "With unit {}, printing input '{}' connected with output of "
                        "type '{}' from unit '{}' is not supported".format(
                            input.model.name,
                            input.name,
                            type(input.connected_to),
                            input.connected_to.model.name,
                        )
                    )
            else:
                # The input is unconnected.
                _ins.append(
                    (
                        "0,0",
                        "! [unconnected] {in_model_name}:{input_name}".format(
                            in_model_name=input.model.name, input_name=input.name
                        ),
                    )
                )
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")
        return str(head) + core + "\n"
