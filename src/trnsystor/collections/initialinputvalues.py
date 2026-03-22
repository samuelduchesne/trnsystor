"""InitialInputValuesCollection module."""

from trnsystor.quantity import Quantity

from trnsystor.collections.variable import VariableCollection
from trnsystor.statement import Constant, Equation
from trnsystor.typevariable import TypeVariable
from trnsystor.utils import _parse_value


class InitialInputValuesCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Initial Input Values.

    Hint:
        Iterating over `InitialInputValuesCollection` will not pass Inputs that
        considered ``questions``. For example, Type15 (printer) has a question for
        the number of variables to be printed by the component. This question can be
        accessed with `.inputs[
        "How_many_variables_are_to_be_printed_by_this_component_"]` to
        modify the number of values. But when iterating over the initial inputs,
        the question will not be returned in the iterator; only regular inputs will.
    """

    def __repr__(self):
        """Return repr(self)."""
        num_inputs = f"{self.size} Initial Input Values:\n"
        try:
            inputs = "\n".join(
                [f'"{key}": {value.value:~P}' for key, value in self.data.items()]
            )
        except ValueError:
            # ~P formatting (above) can fail on strings
            inputs = "\n".join(
                [f'"{key}": {value.value}' for key, value in self.data.items()]
            )
        return num_inputs + inputs

    def __iter__(self):
        """Iterate over inputs except questions."""
        return iter({k: v for k, v in self.data.items() if not v._is_question})

    def __getitem__(self, key):
        """Get item."""
        if isinstance(key, int):
            value = list(self.values())[key]
        elif isinstance(key, slice):
            value = list(self.data.values()).__getitem__(key)
        else:
            value = super(VariableCollection, self).__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """Set item."""
        if isinstance(value, TypeVariable):
            """if a TypeVariable is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, int | float | str):
            """a str, float, int, etc. is passed"""
            existing = (
                self.data[key]
                if isinstance(key, str)
                else list(self.data.values())[key]
            )
            value = _parse_value(
                value, existing.type, existing.unit, (existing.min, existing.max)
            )
            existing.__setattr__("value", value)
        elif isinstance(value, Quantity):
            existing_q = (
                self.data[key]
                if isinstance(key, str)
                else list(self.data.values())[key]
            )
            ex_val = existing_q.value
            target_units = ex_val.units if isinstance(ex_val, Quantity) else None
            new_val = value.to(target_units) if target_units is not None else value
            existing_q.__setattr__("value", new_val)
        elif isinstance(value, Equation | Constant):
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                f"Cannot set a default value of type {type(value)} in this "
                "VariableCollection"
            )

    def _to_deck(self):
        """Return deck representation of self."""
        from trnsystor.serialization.variables import serialize_initial_input_values

        return serialize_initial_input_values(self)
