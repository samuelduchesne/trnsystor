"""DerivativesCollection module."""

import tabulate

from trnsystor.collections.variable import VariableCollection


class DerivativesCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Derivatives."""

    def __repr__(self):
        """Return repr(self)."""
        num_inputs = f"{self.size} Inputs:\n"
        inputs = "\n".join(
            [f'"{key}": {value.value:~P}' for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Return deck representation of self."""
        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        head = f"DERIVATIVES {self.size}\n"
        _ins = [
            (derivative.value.m, f"! {derivative.name}")
            for derivative in self.values()
        ]
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")

        return head + core + "\n"
