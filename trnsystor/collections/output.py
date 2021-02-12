"""OutputCollection module."""
from trnsystor.collections.variable import VariableCollection


class OutputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Outputs."""

    def __repr__(self):
        """Return repr(self)."""
        num_inputs = "{} Outputs:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs
