import collections
import itertools

import tabulate
from sympy import Symbol, Expr

import pyTrnsysType.input_file
from pyTrnsysType import (
    Component,
    StudioHeader,
    TrnsysModel,
    TypeVariable,
    TypeVariableSymbol,
    print_my_latex,
)


class Statement(object):
    """This is the base class for many of the TRNSYS Simulation Control and
    Listing Control Statements. It implements common methods such as the repr()
    method.
    """

    def __init__(self):
        self.doc = ""

    def __repr__(self):
        return self._to_deck()

    def _to_deck(self):
        return ""


class Version(Statement):
    """Added with TRNSYS version 15. The idea of the command is that by labeling
    decks with the TRNSYS version number that they were created under, it is
    easy to keep TRNSYS backwards compatible. The version number is saved by the
    TRNSYS kernel and can be acted upon.
    """

    def __init__(self, v=(18, 0)):
        """Initialize the Version statement

        Args:
            v (tuple): A tuple of (major, minor) eg. 18.0 :> (18, 0)
        """
        super().__init__()
        self.v = v
        self.doc = "The VERSION Statement"

    @classmethod
    def from_string(cls, string):
        """
        Args:
            string:
        """
        return cls(tuple(map(int, string.split("."))))

    def _to_deck(self):
        return "VERSION {}".format(".".join(map(str, self.v)))


class Simulation(Statement):
    """The SIMULATION statement is required for all simulations, and must be
    placed in the TRNSYS input file prior to the first UNIT-TYPE statement. The
    simulation statement determines the starting and stopping times of the
    simulation as well as the time step to be used.
    """

    def __init__(self, start=0, stop=8760, step=1):
        """Initialize the Simulation statement

        Attention:
            With TRNSYS 16 and beyond, the starting time is now specified as the
            time at the beginning of the first time step.

        Args:
            start (int): The hour of the year at which the simulation is to
                begin.
            stop (int): The hour of the year at which the simulation is to end.
            step (float): The time step to be used (hours).
        """
        super().__init__()
        self.start = start
        self.stop = stop
        self.step = step
        self.doc = "Start time\tEnd time\tTime step"

    def _to_deck(self):
        """SIMULATION to tf Δt"""
        return "SIMULATION {} {} {}".format(self.start, self.stop, self.step)


class Tolerances(Statement):
    """The TOLERANCES statement is an optional control statement used to specify
    the error tolerances to be used during a TRNSYS simulation.
    """

    def __init__(self, epsilon_d=0.01, epsilon_a=0.01):
        """
        Args:
            epsilon_d: is a relative (and -epsilon_d is an absolute) error
                tolerance controlling the integration error.
            epsilon_a: is a relative (and -epsilon_a is an absolute) error
                tolerance controlling the convergence of input and output
                variables.
        """
        super().__init__()
        self.epsilon_d = epsilon_d
        self.epsilon_a = epsilon_a
        self.doc = "Integration\tConvergence"

    def _to_deck(self):
        """TOLERANCES 0.001 0.001"""
        head = "TOLERANCES {} {}".format(self.epsilon_d, self.epsilon_a)
        return str(head)


class Limits(Statement):
    """The LIMITS statement is an optional control statement used to set limits
    on the number of iterations that will be performed by TRNSYS during a time
    step before it is determined that the differential equations and/or
    algebraic equations are not converging.
    """

    def __init__(self, m=25, n=10, p=None):
        """
        Args:
            m (int): is the maximum number of iterations which can be performed
                during a time-step before a WARNING message is printed out.
            n (int): is the maximum number of WARNING messages which may be
                printed before the simulation terminates in ERROR.
            p (int, optional): is an optional limit. If any component is called
                p times in one time step, then the component will be traced (See
                Section 2.3.5) for all subsequent calls in the timestep. When p
                is not specified by the user, TRNSYS sets p equal to m.
        """
        super().__init__()
        self.m = m
        self.n = n
        self.p = p if p is not None else self.m
        self.doc = "Max iterations\tMax warnings\tTrace limit"

    def _to_deck(self):
        """TOLERANCES 0.001 0.001"""
        head = "LIMITS {} {} {}".format(self.m, self.n, self.p)
        return str(head)


class NaNCheck(Statement):
    """One problem that has plagued TRNSYS simulation debuggers is that in
    Fortran, the “Not a Number” (NaN) condition can be passed along through
    numerous subroutines without being flagged as an error. For example, a
    division by zero results in a variable being set to NaN. This NaN can then
    be used in subsequent equation, causing them to be set to NaN as well. The
    problem persists for a time until a Range Check or an Integer Overflow error
    occurs and actually stops simulation progress. To alleviate the problem, the
    NAN_CHECK Statement was added as an optional debugging feature in TRNSYS
    input files.
    """

    def __init__(self, n=0):
        """Initialize a NaNCheck object.

        Hint:
            If the NAN_CHECK statement is present (n=1), then the TRNSYS kernel
            checks every output of each component at each iteration and
            generates a clean error if ever one of those outputs has been set to
            the FORTRAN NaN condition. Because this checking is very time
            consuming, users are not advised to leave NAN_CHECK set in their
            input files as it causes simulations to run much more slowly.

        Args:
            n (int): Is 0 if the NAN_CHECK feature is not desired or 1 if
                NAN_CHECK feature is desired. Default is 0.
        """
        super().__init__()
        self.n = int(n)
        self.doc = "The NAN_CHECK Statement"

    def _to_deck(self):
        return "NAN_CHECK {}".format(self.n)


class OverwriteCheck(Statement):
    """A common error in non standard and user written TRNSYS Type routines is
    to reserve too little space in the global output array. By default, each
    Type is accorded 20 spots in the global TRNSYS output array. However, there
    is no way to prevent the Type from then writing in (for example) the 21st
    spot; the entire global output array is always accessible. By activating the
    OVERWRITE_CHECK statement, the TRNSYS kernel checks to make sure that each
    Type did not write outside its allotted space. As with the NAN_CHECK
    statement, OVERWRITE_CHECK is a time consuming process and should only be
    used as a debugging tool when a simulation is ending in error.
    """

    def __init__(self, n=0):
        """Initialize an OVERWRITE_CHECK object.

        Hint:
            OVERWRITE_CHECK is a time consuming process and should only be used
            as a debugging tool when a simulation is ending in error.

        Args:
            n (int): Is 0 if the OVERWRITE_CHECK feature is not desired or 1 if
                OVERWRITE_CHECK feature is desired.
        """
        super().__init__()
        self.n = int(n)
        self.doc = "The OVERWRITE_CHECK Statement"

    def _to_deck(self):
        return "OVERWRITE_CHECK {}".format(self.n)


class TimeReport(Statement):
    """The statement TIME_REPORT turns on or off the internal calculation of the
    time spent on each unit. If this feature is desired, the listing file will
    contain this information at the end of the file.
    """

    def __init__(self, n=0):
        """Initialize a TIME_REPORT object.

        Args:
            n (int): Is 0 if the TIME_REPORT feature is not desired or 1 if
                TIME_REPORT feature is desired.
        """
        super().__init__()
        self.n = n
        self.doc = "The TIME_REPORT Statement"

    def _to_deck(self):
        return "TIME_REPORT {n}".format(n=self.n)


class List(Statement):
    """The LIST statement is used to turn on the TRNSYS processor listing after
    it has been turned off by a NOLIST statement.
    """

    def __init__(self, activate=False):
        """Hint:
            The listing is assumed to be on at the beginning of a TRNSYS input
            file. As many LIST cards as desired may appear in a TRNSYS input
            file and may be located anywhere in the input file.

        Args:
            activate (bool):
        """
        super().__init__()
        self.activate = activate
        self.doc = "The LIST Statement"


class DFQ(Statement):
    """The optional DFQ card allows the user to select one of three algorithms
    built into TRNSYS to numerically solve differential equations (see Manual
    08-Programmer’s Guide for additional information about solution of
    differential equations).
    """

    def __init__(self, k=1):
        """Initialize the Differential Equation Solving Method Statement

        Args:
            k (int, optional): an integer between 1 and 3. If a DFQ card is not
                present in the TRNSYS input file, DFQ 1 is assumed.

        Note:
            The three numerical integration algorithms are:

            1. Modified-Euler method (a 2nd order Runge-Kutta method)
            2. Non-self-starting Heun's method (a 2nd order Predictor-Corrector
               method)
            3. Fourth-order Adams method (a 4th order Predictor-Corrector
               method)
        """
        super().__init__()
        self.k = k
        self.doc = "TRNSYS numerical integration solver method"

    def _to_deck(self):
        return str("DFQ {}".format(self.k))


class Width(Statement):
    """The WIDTH statement is an optional control statement is used to set the
    number of characters to be allowed on a line of TRNSYS output.

    Note:
        This statement is obsolete.
    """

    def __init__(self, n=120):
        """Initialize the Width Statement.

        Args:
            n (int, optional): n is the number of characters per printed line; n
                must be between 72 and 132.
        """
        super().__init__()
        self.k = self._check_range(int(n))
        self.doc = "The number of printed characters per line"

    def _to_deck(self):
        return str("WIDTH {}".format(self.k))

    @staticmethod
    def _check_range(n):
        """
        Args:
            n:
        """
        if n >= 72 and n <= 132:
            return n
        else:
            raise ValueError("The Width Statement mus be between 72 and 132.")


class NoCheck(Statement):
    """TRNSYS allows up to 20 different INPUTS to be removed from the list of
    INPUTS to be checked for convergence (see Section 1.9).
    """

    def __init__(self, inputs=None):
        """
        Args:
            inputs (list of Input):
        """
        super().__init__()
        if not inputs:
            inputs = []
        if len(inputs) > 20:
            raise ValueError(
                "TRNSYS allows only up to 20 different INPUTS to " "be removed"
            )
        self.inputs = inputs
        self.doc = "CHECK Statement"

    def _to_deck(self):
        head = "NOCHECK {}\n".format(len(self.inputs))
        core = "\t".join(
            [
                "{}, {}".format(input.model.unit_number, input.one_based_idx)
                for input in self.inputs
            ]
        )
        return str(head) + str(core)


class NoList(Statement):
    """The NOLIST statement is used to turn off the listing of the TRNSYS input
    file.
    """

    def __init__(self, active=True):
        """
        Args:
            active (bool): Setting active to True will add the NOLIST statement
        """
        super().__init__()
        self.active = active
        self.doc = "NOLIST statement"

    def _to_deck(self):
        return "NOLIST" if self.active else ""


class Map(Statement):
    """The MAP statement is an optional control statement that is used to obtain
    a component output map listing which is particularly useful in debugging
    component interconnections.
    """

    def __init__(self, active=True):
        """Setting active to True will add the MAP statement

        Args:
            active (bool): Setting active to True will add the MAP statement
        """
        super().__init__()
        self.active = active
        self.doc = "MAP statement"

    def _to_deck(self):
        return "MAP" if self.active else ""


class EqSolver(Statement):
    """With the release of TRNSYS 16, new methods for solving blocks of
    EQUATIONS statements were added. For additional information on EQUATIONS
    statements, please refer to section 6.3.9. The order in which blocks of
    EQUATIONS are solved is controlled by the EQSOLVER statement.
    """

    def __init__(self, n=0):
        """Hint:
            :attr:`n` can have any of the following values:

            1. n=0 (default if no value is provided) if a component output or
               TIME changes, update the block of equations that depend upon
               those values. Then update components that depend upon the first
               block of equations. Continue looping until all equations have
               been updated appropriately. This equation blocking method is most
               like the method used in TRNSYS version 15 and before.
            2. n=1 if a component output or TIME changes by more than the value
               set in the TOLERANCES Statement (see Section 6.3.3), update the
               block of equations that depend upon those values. Then update
               components that depend upon the first block of equations.
               Continue looping until all equations have been updated
               appropriately.
            3. n=2 treat equations as a component and update them only after
               updating all components.

        Args:
            n (int): The order in which the equations are solved.
        """
        super().__init__()
        self.n = n
        self.doc = "EQUATION SOLVER statement"

    def _to_deck(self):
        return "EQSOLVER {}".format(self.n)


class End(Statement):
    """The END statement must be the last line of a TRNSYS input file. It
    signals the TRNSYS processor that no more control statements follow and that
    the simulation may begin.
    """

    def __init__(self):
        super().__init__()
        self.doc = "The END Statement"

    def _to_deck(self):
        return "END"


class Solver(Statement):
    """A SOLVER command has been added to TRNSYS to select the computational
    scheme. The optional SOLVER card allows the user to select one of two
    algorithms built into TRNSYS to numerically solve the system of algebraic
    and differential equations.
    """

    def __init__(self, k=0, rf_min=1, rf_max=1):
        """
        Args:
            k (int): the solution algorithm.
            rf_min (float): the minimum relaxation factor.
            rf_max (float): the maximum relaxation factor.

        Note:
            k is either the integer 0 or 1. If a SOLVER card is not present in
            the TRNSYS input file, SOLVER 0 is assumed. If k = 0, the SOLVER
            statement takes two additional parameters, RFmin and RFmax:

            The two solution algorithms (k) are:
                * 0: Successive Substitution
                * 1: Powell’s Method
        """
        super().__init__()
        self.rf_max = rf_max
        self.rf_min = rf_min
        self.k = k
        self.doc = (
            "Solver statement\tMinimum relaxation factor\tMaximum " "relaxation factor"
        )

    def _to_deck(self):
        return (
            "SOLVER {} {} {}".format(self.k, self.rf_min, self.rf_max)
            if self.k == 0
            else "SOLVER {}".format(self.k)
        )


class Constant(Statement):
    """The CONSTANTS statement is useful when simulating a number of systems
    with identical component configurations but with different parameter values,
    initial input values, or initial values of time dependent variables.
    """

    _new_id = itertools.count(start=1)
    instances = {}

    def __init__(self, name=None, equals_to=None, doc=None):
        """
        Args:
            name (str): The left hand side of the equation.
            equals_to (str, TypeVariable): The right hand side of the equation.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        super().__init__()
        try:
            c_ = Constant.instances[name]
        except:
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
        """Create a Constant from a string expression. Anything before the equal
        sign ("=") will become the Constant's name and anything after will
        become the equality statement.

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
        """The equation number. Unique"""
        return self._n

    def _to_deck(self):
        return self.equals_to


class ConstantCollection(collections.UserDict, Component):
    """A class that behaves like a dict and that collects one or more
    :class:`Constants`.

    You can pass a dict of Equation or you can pass a list of Equation. In
    the latter, the :attr:`Equation.name` attribute will be used as a key.
    """

    def __init__(self, mutable=None, name=None):
        """Initialize a new ConstantCollection.

        Example:
            >>> c_1 = Constant.from_expression("A = 1")
            >>> c_2 = Constant.from_expression("B = 2")
            >>> ConstantCollection([c_1, c_2])

        Args:
            mutable (Iterable, optional): An iterable.
            name (str): A user defined name for this collection of constants.
                This name will be used to identify this block of constants in
                the .dck file;
        """
        if isinstance(mutable, list):
            _dict = {f.name: f for f in mutable}
        else:
            _dict = mutable
        super().__init__(_dict)
        self.name = pyTrnsysType.input_file.Name(name)
        self.studio = StudioHeader.from_component(self)
        self._unit = next(TrnsysModel.new_id)

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        value = super().__getitem__(key)
        return value

    def __repr__(self):
        return self._to_deck()

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def update(self, E=None, **F):
        """D.update([E, ]**F). Update D from a dict/list/iterable E and F.
        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for cts.name,
        cts in E: D[cts.name] = cts
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (list, dict or Constant): The constant to add or update in D (
                self).
            F (list, dict or Constant): Other constants to update are passed.
        """
        if isinstance(E, Constant):
            E.model = self
            _e = {E.name: E}
        elif isinstance(E, list):
            _e = {cts.name: cts for cts in E}
        else:
            for v in E.values():
                if not isinstance(v, Constant):
                    raise TypeError(
                        "Can only update an ConstantCollection with a"
                        "Constant, not a {}".format(type(v))
                    )
            _e = {v.name: v for v in E.values()}
        k: Constant
        for k in F:
            if isinstance(F[k], dict):
                _f = {v.name: v for k, v in F.items()}
            elif isinstance(F[k], list):
                _f = {cts.name: cts for cts in F[k]}
            else:
                raise TypeError(
                    "Can only update an ConstantCollection with a"
                    "Constant, not a {}".format(type(F[k]))
                )
            _e.update(_f)
        super(ConstantCollection, self).update(_e)

    @property
    def size(self):
        return len(self)

    @property
    def unit_number(self):
        return self._unit

    def _to_deck(self):
        """To deck representation

        Examples::

            CONSTANTS n
            NAME1 = ... constant 1 ...
            NAME2 = ... constant 2 ...
            •
            •
            •
            NAMEn = ... constant n ...
        """
        header_comment = '* CONSTANTS "{}"\n\n'.format(self.name)
        head = "CONSTANTS {}\n".format(len(self))
        v_ = ((equa.name, "=", str(equa)) for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return str(header_comment) + str(head) + str(core)

    def _get_inputs(self):
        """inputs getter. Sorts by order number each time it is called
        """
        return self

    def _get_outputs(self):
        """outputs getter. Since self is already a  dict, return self.
        """
        return self


class Equation(Statement):
    """The EQUATIONS statement allows variables to be defined as algebraic
    functions of constants, previously defined variables, and outputs from
    TRNSYS components. These variables can then be used in place of numbers in
    the TRNSYS input file to represent inputs to components; numerical values of
    parameters; and initial values of inputs and time-dependent variables. The
    capabilities of the EQUATIONS statement overlap but greatly exceed those of
    the CONSTANTS statement described in the previous section.

    Hint:
        In pyTrnsysType, the Equation class works hand in hand with the
        :class:`EquationCollection` class. This class behaves a little bit like
        the equation component in the TRNSYS Studio, meaning that you can list
        equation in a block, give it a name, etc. See the
        :class:`EquationCollection` class for more details.
    """

    _new_id = itertools.count(start=1)

    def __init__(self, name=None, equals_to=None, doc=None, model=None):
        """
        Args:
            name (str): The left hand side of the equation.
            equals_to (str, TypeVariable): The right hand side of the equation.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        super().__init__()
        self._n = next(self._new_id)
        self.name = name
        self.equals_to = equals_to
        self.doc = doc
        self.model = model  # the TrnsysModel this Equation belongs to.

        self._connected_to = None

    def __repr__(self):
        return " = ".join([self.name, self._to_deck()])

    def __str__(self):
        return self.__repr__()

    @classmethod
    def from_expression(cls, expression, doc=None):
        """Create an equation from a string expression. Anything before the
        equal sign ("=") will become a Constant and anything after will become
        the equality statement.

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
        """Crate an equation with a combination of a generic expression (with
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

            >>> from pyTrnsysType import TrnsysModel
            >>> fan = TrnsysModel.from_xml("fan_type.xml")
            >>> vars = (fan.outputs[0], fan.outputs[1])

            .. Important::

                The order of the symbolic variable encountered in the string
                expression (step 2), from left to right, must be the same for
                the tuple of variables. For instance, `a` is followed by `b`,
                therefore `fan.outputs[0]` is followed by `fan.outputs[1]`.

            4. finally, we create the Equation. Note that vars is passed with
            the '*' declaration to unpack the tuple.

            >>> from pyTrnsysType.input_file import Equation
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
        return cls(name, exp)

    @property
    def eq_number(self):
        """The equation number. Unique"""
        return self._n

    @property
    def idx(self):
        """The 0-based index of the Equation"""
        ns = {e: i for i, e in enumerate(self.model)}
        return ns[self.name]

    @property
    def one_based_idx(self):
        """The 1-based index of the Equation"""
        return self.idx + 1

    @property
    def unit_number(self):
        return self.model.unit_number

    @property
    def is_connected(self):
        """Whether or not this TypeVariable is connected to another type"""
        return self.connected_to is not None

    @property
    def connected_to(self):
        """The TrnsysModel to which this component is connected"""
        return self._connected_to

    def _to_deck(self):
        if isinstance(self.equals_to, TypeVariable):
            return "[{unit_number}, {output_id}]".format(
                unit_number=self.equals_to.model.unit_number,
                output_id=self.equals_to.one_based_idx,
            )
        elif isinstance(self.equals_to, Expr):
            return print_my_latex(self.equals_to)
        else:
            return self.equals_to


class EquationCollection(collections.UserDict, Component):
    """A class that behaves like a dict and that collects one or more
    :class:`Equations`. This class behaves a little bit like the equation
    component in the TRNSYS Studio, meaning that you can list equation in a
    block, give it a name, etc.

    You can pass a dict of Equation or you can pass a list of Equation. In
    this case, the :attr:`Equation.name` attribute will be used as a key.

    Hint:
        Creating equations in PyTrnsysType is done trough the :class:`Equation`
        class. Equations are than collected in this EquationCollection. See the
        :class:`Equation` class for more details.
    """

    def __init__(self, mutable=None, name=None):
        """Initialize a new EquationCollection.

        Example:
            >>> equa1 = Equation.from_expression("TdbAmb = [011,001]")
            >>> equa2 = Equation.from_expression("rhAmb = [011,007]")
            >>> EquationCollection([equa1, equa2])

        Args:
            mutable (Iterable, optional): An iterable (dict or list).
            name (str): A user defined name for this collection of equations.
                This name will be used to identify this block of equations in
                the .dck file;
        """
        if isinstance(mutable, list):
            _dict = {f.name: f for f in mutable}
        else:
            _dict = mutable
        super().__init__(_dict)
        self.name = pyTrnsysType.input_file.Name(name)
        self._unit = next(TrnsysModel.new_id)
        self.studio = StudioHeader.from_component(self)

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super().__getitem__(key)
        return value

    # def __hash__(self):
    #     return self.unit_number

    def __repr__(self):
        return self._to_deck()

    def __setitem__(self, key, value):
        # optional processing here
        value.model = self
        super().__setitem__(key, value)

    def __hash__(self):
        return self._unit

    def update(self, E=None, **F):
        """D.update([E, ]**F). Update D from a dict/list/iterable E and F.
        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for eq.name,
        eq in E: D[eq.name] = eq
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (list, dict or Equation): The equation to add or update in D (
                self).
            F (list, dict or Equation): Other Equations to update are passed.

        Returns:
            None
        """
        if isinstance(E, Equation):
            E.model = self
            _e = {E.name: E}
        elif isinstance(E, list):
            _e = {eq.name: eq for eq in E}
        else:
            for v in E.values():
                if not isinstance(v, Equation):
                    raise TypeError(
                        "Can only update an EquationCollection with an"
                        "Equation, not a {}".format(type(v))
                    )
            _e = {v.name: v for v in E.values()}
        k: Equation
        for k in F:
            if isinstance(F[k], dict):
                _f = {v.name: v for k, v in F.items()}
            elif isinstance(F[k], list):
                _f = {eq.name: eq for eq in F[k]}
            else:
                raise TypeError(
                    "Can only update an EquationCollection with an"
                    "Equation, not a {}".format(type(F[k]))
                )
            _e.update(_f)
        super(EquationCollection, self).update(_e)

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]

    @property
    def size(self):
        return len(self)

    @property
    def unit_number(self):
        return self._unit

    @property
    def unit_name(self):
        """This type does not have a unit_name. Return component name"""
        return self.name

    @property
    def model(self):
        """This model does not have a proforma. Return class name."""
        return self.__class__.__name__

    def _to_deck(self):
        """To deck representation

        Examples::

            EQUATIONS n
            NAME1 = ... equation 1 ...
            NAME2 = ... equation 2 ...
            •
            •
            •
            NAMEn = ... equation n ...
        """
        header_comment = '* EQUATIONS "{}"\n\n'.format(self.name)
        head = "EQUATIONS {}\n".format(len(self))
        v_ = ((equa.name, "=", equa._to_deck()) for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return str(header_comment) + str(head) + str(core)

    def _get_inputs(self):
        """inputs getter. Sorts by order number each time it is called
        """
        return self

    def _get_outputs(self):
        """outputs getter. Since self is already a  dict, return self.
        """
        return self

    def _get_ordered_filtered_types(self, classe_, store):
        """
        Args:
            classe_:
            store:
        """
        return collections.OrderedDict(
            (attr, self._meta[store][attr])
            for attr in sorted(
                self._get_filtered_types(classe_, store),
                key=lambda key: self._meta[store][key].order,
            )
        )

    def _get_filtered_types(self, classe_, store):
        """
        Args:
            classe_:
            store:
        """
        return filter(
            lambda kv: isinstance(self._meta[store][kv], classe_), self._meta[store]
        )
