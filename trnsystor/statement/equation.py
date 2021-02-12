"""Equation module."""
import itertools

from sympy import Expr, Symbol

from trnsystor.statement.constant import Constant
from trnsystor.statement.statement import Statement
from trnsystor.typevariable import TypeVariable
from trnsystor.utils import TypeVariableSymbol, print_my_latex


class Equation(Statement, TypeVariable):
    """EQUATION Statement.

    The EQUATIONS statement allows variables to be defined as algebraic
    functions of constants, previously defined variables, and outputs from
    TRNSYS components. These variables can then be used in place of numbers in
    the TRNSYS input file to represent inputs to components; numerical values of
    parameters; and initial values of inputs and time-dependent variables. The
    capabilities of the EQUATIONS statement overlap but greatly exceed those of
    the CONSTANTS statement described in the previous section.

    Hint:
        In trnsystor, the Equation class works hand in hand with the
        :class:`EquationCollection` class. This class behaves a little bit like
        the equation component in the TRNSYS Studio, meaning that you can list
        equation in a block, give it a name, etc. See the
        :class:`EquationCollection` class for more details.
    """

    _new_id = itertools.count(start=1)

    def __init__(self, name=None, equals_to=None, doc=None, model=None):
        """Initialize object.

        Args:
            name (str): The left hand side of the equation.
            equals_to (str, TypeVariable): The right hand side of the equation.
            doc (str, optional): A small description optionally printed in the
                deck file.
            model (Component): The TrnsysModel this Equation belongs to.
        """
        super().__init__()
        self._n = next(self._new_id)
        self.name = name
        self.equals_to = equals_to
        self.doc = doc
        self.model = model  # the TrnsysModel this Equation belongs to.

    def __repr__(self):
        """Return repr(self)."""
        return " = ".join([self.name, self._to_deck()])

    def __str__(self):
        """Return repr(self)."""
        return repr(self)

    @classmethod
    def from_expression(cls, expression, doc=None):
        """Create an equation from a string expression.

        Anything before the equal sign ("=") will become a Constant and anything
        after will become the equality statement.

        Example:
            Create a simple expression like so:

            >>> equa1 = Equation.from_expression("TdbAmb = [011,001]")

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

    @classmethod
    def from_symbolic_expression(cls, name, exp, *args, doc=None):
        """Create an equation from symbolic expression.

        Crate an equation with a combination of a generic expression (with
        placeholder variables) and a list of arguments. The underlying engine
        will use Sympy and symbolic variables. You can use a mixture of
        :class:`TypeVariable` and :class:`Equation`, :class:`Constant` as
        well as the python default :class:`str`.

        .. Important::

            If a `str` is passed in place of an expression argument (
            :attr:`args`), make sure to declare that string as an Equation or
            a Constant later in the routine.

        Examples:
            In this example, we define a variable (var_a) and we want it to be
            equal to the 'Outlet Air Humidity Ratio' divided by 12 + log(
            Temperature to heat source). In a TRNSYS deck file one would have to
            manually determine the unit numbers and output numbers and write
            something like : '[1, 2]/12 + log([1, 1])'. With the
            :func:`~from_symbolic_expression`, we can do this very simply:

            1. first, define the name of the variable:

            >>> name = "var_a"

            2. then, define the expression as a string. Here, the variables `a`
            and `b` are symbols that represent the two type outputs. Note that
            their name has bee chosen arbitrarily.

            >>> exp = "log(a) + b / 12"
            >>> # would be also equivalent to
            >>> exp = "log(x) + y / 12"

            3. here, we define the actual variables (the type outputs) after
            loading our model from its proforma:

            >>> from trnsystor import TrnsysModel
            >>> fan = TrnsysModel.from_xml("fan_type.xml")
            >>> vars = (fan.outputs[0], fan.outputs[1])

            .. Important::

                The order of the symbolic variable encountered in the string
                expression (step 2), from left to right, must be the same for
                the tuple of variables. For instance, `a` is followed by `b`,
                therefore `fan.outputs[0]` is followed by `fan.outputs[1]`.

            4. finally, we create the Equation. Note that vars is passed with
            the '*' declaration to unpack the tuple.

            >>> from trnsystor.statement import Equation
            >>> eq = Equation.from_symbolic_expression(name, exp, *vars)
            >>> print(eq)
            [1, 1]/12 + log([1, 2])

        Args:
            name (str): The name of the variable (left-hand side), of the
                equation.
            exp (str): The expression to evaluate. Use any variable name and
                mathematical expression.
            *args (tuple): A tuple of :class:`TypeVariable` that will replace
                the any variable name specified in the above expression.
            doc (str, optional): A small description optionally printed in the
                deck file.

        Returns:
            Equation: The Equation Statement object.
        """
        from sympy.parsing.sympy_parser import parse_expr

        exp = parse_expr(exp)

        if len(exp.free_symbols) != len(args):
            raise AttributeError(
                "The expression does not have the same number of "
                "variables as arguments passed to the symbolic expression "
                "parser."
            )
        for i, arg in enumerate(sorted(exp.free_symbols, key=lambda sym: sym.name)):
            new_symbol = args[i]
            if isinstance(new_symbol, TypeVariable):
                exp = exp.subs(arg, TypeVariableSymbol(new_symbol))
            elif isinstance(new_symbol, (Equation, Constant)):
                exp = exp.subs(arg, Symbol(new_symbol.name))
            else:
                exp = exp.subs(arg, Symbol(new_symbol))
        return cls(name, exp, doc=doc)

    @property
    def eq_number(self):
        """Return the equation number (unique)."""
        return self._n

    @property
    def idx(self):
        """Return the 0-based index of the Equation."""
        ns = {e: i for i, e in enumerate(self.model)}
        return ns[self.name]

    @property
    def unit_number(self):
        """Return the unit number of the EquationCollection self belongs to."""
        return self.model.unit_number

    def _to_deck(self):
        """Return deck representation of self."""
        if isinstance(self.equals_to, TypeVariable):
            return "[{unit_number}, {output_id}]".format(
                unit_number=self.equals_to.model.unit_number,
                output_id=self.equals_to.one_based_idx,
            )
        elif isinstance(self.equals_to, Expr):
            return print_my_latex(self.equals_to)
        else:
            return self.equals_to
