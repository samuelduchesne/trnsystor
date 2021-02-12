"""Parameter module."""
import tabulate
from pint.quantity import _Quantity

from trnsystor.collections.variable import VariableCollection
from trnsystor.statement import Equation
from trnsystor.typevariable import TypeVariable


class ParameterCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Parameters."""

    def __repr__(self):
        """Return repr(self)."""
        num_inputs = "{} Parameters:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Return deck representation of self."""
        head = "PARAMETERS {}\n".format(self.size)
        # loop through parameters and print the (value, name) tuples.
        v_ = []
        param: TypeVariable
        for param in self.values():
            if not param._is_question:
                if isinstance(param.value, Equation):
                    v_.append(
                        (
                            param.value.name,
                            "! {} {}".format(param.one_based_idx, param.name),
                        )
                    )
                elif isinstance(param.value, _Quantity):
                    v_.append(
                        (
                            param.value.m,
                            "! {} {}".format(param.one_based_idx, param.name),
                        )
                    )
                else:
                    raise NotImplementedError(
                        "Printing parameter '{}' of type '{}' from unit '{}' is not "
                        "supported".format(
                            param.name, type(param.value), param.model.name
                        )
                    )
        params_str = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return head + params_str + "\n"

    @property
    def size(self):
        """Return the number of inputs."""
        return len([p for p in self if not self[p]._is_question])
