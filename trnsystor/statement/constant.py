"""Constant module."""
import itertools

from trnsystor.statement.statement import Statement


class Constant(Statement):
    """CONSTANTS Statement.

    The CONSTANTS statement is useful when simulating a number of systems
    with identical component configurations but with different parameter values,
    initial input values, or initial values of time dependent variables.
    """

    _new_id = itertools.count(start=1)
    instances = {}

    def __init__(self, name=None, equals_to=None, doc=None):
        """Initialize object.

        Args:
            name (str): The left hand side of the equation.
            equals_to (str, TypeVariable): The right hand side of the equation.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        super().__init__()
        try:
            c_ = Constant.instances[name]
        except KeyError:
            self._n = next(self._new_id)
            self.name = name
            self.equals_to = equals_to
            self.doc = doc
        else:
            self._n = c_._n
            self.name = c_.name
            self.equals_to = c_.equals_to
            self.doc = c_.doc
        finally:
            Constant.instances.update({self.name: self})

    @classmethod
    def from_expression(cls, expression, doc=None):
        """Create a Constant from a string expression.

        Anything before the equal sign ("=") will become the Constant's name and
        anything after will become the equality statement.

        Hint:
            The simple expressions are processed much as FORTRAN arithmetic
            statements are, with one significant exceptions. Expressions are
            evaluated from left to right with no precedence accorded to any
            operation over another. This rule must constantly be borne in mind
            when writing long expressions.

        Args:
            expression (str): A user-defined expression to parse.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        if "=" not in expression:
            raise ValueError(
                "The from_expression constructor must contain an expression "
                "with the equal sign"
            )
        a, b = expression.split("=")
        return cls(a.strip(), b.strip(), doc=doc)

    @property
    def constant_number(self):
        """The equation number (unique)."""
        return self._n

    def _to_deck(self):
        """Return deck representation of self."""
        return self.equals_to
