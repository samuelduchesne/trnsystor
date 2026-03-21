"""DerivativesCollection module."""


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
        from trnsystor.serialization.variables import serialize_derivatives

        return serialize_derivatives(self)
