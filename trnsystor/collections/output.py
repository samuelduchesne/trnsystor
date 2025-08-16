"""OutputCollection module."""
from trnsystor.collections.variable import VariableCollection


class OutputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Outputs."""

    def __repr__(self):
        """Return repr(self)."""
        num_inputs = f"{self.size} Outputs:\n"
        inputs = "\n".join(
            [f'"{key}": {value.value:~P}' for key, value in self.data.items()]
        )
        return num_inputs + inputs
