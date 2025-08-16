"""Parameter module."""
import tabulate
from pint import Quantity

from trnsystor.collections.variable import VariableCollection
from trnsystor.statement import Equation
from trnsystor.typevariable import TypeVariable


class ParameterCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Parameters."""

    def __repr__(self):
        """Return repr(self)."""
        num_inputs = f"{self.size} Parameters:\n"
        inputs = "\n".join(
            [f'"{key}": {value.value:~P}' for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Return deck representation of self."""
        head = f"PARAMETERS {self.size}\n"
        # loop through parameters and print the (value, name) tuples.
        v_ = []
        param: TypeVariable
        for param in self.values():
            if not param._is_question:
                if isinstance(param.value, Equation):
                    v_.append(
                        (
                            param.value.name,
                            f"! {param.one_based_idx} {param.name}",
                        )
                    )
                elif isinstance(param.value, Quantity):
                    v_.append(
                        (
                            param.value.m,
                            f"! {param.one_based_idx} {param.name}",
                        )
                    )
                else:
                    raise NotImplementedError(
                        f"Printing parameter '{param.name}' of type '{type(param.value)}' from unit '{param.model.name}' is not "
                        "supported"
                    )
        params_str = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return head + params_str + "\n"

    @property
    def size(self):
        """Return the number of inputs."""
        return len([p for p in self if not self[p]._is_question])
