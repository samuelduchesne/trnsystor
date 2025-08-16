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
        num_inputs = f"{self.size} Inputs:\n"
        try:
            inputs = "\n".join(
                [
                    f'"{key}": {value.value:~P}'
                    for key, value in self.data.items()
                ]
            )
        except ValueError:  # Invalid format specifier
            inputs = "\n".join(
                [
                    f'"{key}": {value.value}'
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

        head = f"INPUTS {self.size}\n"
        # "{u_i}, {o_i}": is an integer number referencing the number of the
        # UNIT to which the ith INPUT is connected. is an integer number
        # indicating to which OUTPUT (i.e., the 1st, 2nd, etc.) of UNIT
        # number ui the ith INPUT is connected.
        _ins = []
        for input in self.values():
            if input.is_connected:
                # Equations and Constants behave differently than TypeVariables.
                # Equations and Constants use the name of the variable.
                # TypeVariables use the 0,0 digit tuple.
                if isinstance(input.predecessor, Equation | Constant):
                    _ins.append(
                        (
                            input.predecessor.name,
                            self._help_text(input),
                        )
                    )
                elif isinstance(input.predecessor, TypeVariable):
                    _ins.append(
                        (
                            f"{input.predecessor.model.unit_number},{input.predecessor.one_based_idx}",
                            self._help_text(input),
                        )
                    )
                else:
                    raise NotImplementedError(
                        
                            f"With unit {input.model.name}, printing input "
                            f"'{input.name}' connected with output of "
                            f"type '{type(input.connected_to)}' from unit "
                            f"'{input.connected_to.model.name}' is not supported"
                        
                    )
            else:
                # The input is unconnected.
                _ins.append(
                    (
                        "0,0",
                        f"! [unconnected] {input.model.name}:{input.name}",
                    )
                )
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")
        return str(head) + core + "\n"

    @staticmethod
    def _help_text(input_type):
        """Generate help text for input connection.

        Examples:
            None:flowRateDoubled -> Ecoflex 2-Pipe:Inlet Fluid Flowrate - Pipe 1
        """
        return f"! {input_type.predecessor.model.name}:{input_type.predecessor.name} -> {input_type.model.name}:{input_type.name}"

    @property
    def size(self):
        """Return the number of inputs excluding questions."""
        return len([i for i in self])
