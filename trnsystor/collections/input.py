"""InputCollection module."""


from trnsystor.collections.variable import VariableCollection


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
                [f'"{key}": {value.value:~P}' for key, value in self.data.items()]
            )
        except ValueError:  # Invalid format specifier
            inputs = "\n".join(
                [f'"{key}": {value.value}' for key, value in self.data.items()]
            )
        return num_inputs + inputs

    def __iter__(self):
        """Iterate over inputs except questions."""
        return iter({k: v for k, v in self.data.items() if not v._is_question})

    def _to_deck(self):
        """Return deck representation of self."""
        from trnsystor.serialization.variables import serialize_inputs

        return serialize_inputs(self)

    @staticmethod
    def _help_text(input_type):
        """Generate help text for input connection.

        Examples:
            None:flowRateDoubled -> Ecoflex 2-Pipe:Inlet Fluid Flowrate - Pipe 1
        """
        return (
            f"! {input_type.predecessor.model.name}:"
            f"{input_type.predecessor.name} -> "
            f"{input_type.model.name}:{input_type.name}"
        )

    @property
    def size(self):
        """Return the number of inputs excluding questions."""
        return len(list(self))
