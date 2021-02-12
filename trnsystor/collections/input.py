"""InputCollection module."""
import tabulate

from trnsystor.collections.variable import VariableCollection
from trnsystor.statement import Constant, Equation
from trnsystor.typevariable import TypeVariable


class InputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Inputs.

    Hint:
        Iterating over `InputCollection` will not pass Inputs that considered
        ``questions``. For example, Type15 (printer) has a question for the number
        of variables to be printed by the component. This question can be accessed
        with `.inputs["How_many_variables_are_to_be_printed_by_this_component_"]` to
        modify the number of values. But when iterating over the inputs, the question
        will not be returned in the iterator; only regular inputs will.
    """

    def __repr__(self):
        """Return Deck representation of self."""
        num_inputs = "{} Inputs:\n".format(self.size)
        try:
            inputs = "\n".join(
                [
                    '"{}": {:~P}'.format(key, value.value)
                    for key, value in self.data.items()
                ]
            )
        except ValueError:  # Invalid format specifier
            inputs = "\n".join(
                [
                    '"{}": {}'.format(key, value.value)
                    for key, value in self.data.items()
                ]
            )
        return num_inputs + inputs

    def __iter__(self):
        """Iterate over inputs except questions."""
        return iter({k: v for k, v in self.data.items() if not v._is_question})

    def _to_deck(self):
        """Return deck representation of self."""
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

    @property
    def size(self):
        """Return the number of inputs excluding questions."""
        return len([i for i in self])
