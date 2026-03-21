"""Parameter module."""



from trnsystor.collections.variable import VariableCollection


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
        from trnsystor.serialization.variables import serialize_parameters

        return serialize_parameters(self)

    @property
    def size(self):
        """Return the number of inputs."""
        return len([p for p in self.data if not self.data[p]._is_question])
