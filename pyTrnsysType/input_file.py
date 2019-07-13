import collections
import itertools
import logging as lg
import re

import tabulate
from path import Path
from shapely.geometry import LineString, Point
from sympy import Expr, Symbol

from pyTrnsysType import TypeVariable, TrnsysModel, Component, StudioHeader, \
    MetaData, AnchorPoint, ComponentCollection
from pyTrnsysType.statements import Version, NaNCheck, OverwriteCheck, \
    TimeReport, List, Simulation, Tolerances, Limits, \
    DFQ, \
    NoCheck, NoList, Map, EqSolver, End, Solver, Statement, Width
from pyTrnsysType.utils import print_my_latex, TypeVariableSymbol, \
    get_rgb_from_int
from .trnsymodel import ParameterCollection, InputCollection, \
    ExternalFileCollection, _studio_to_linestyle


class Name(object):
    """Handles the attribution of user defined names for :class:`TrnsysModel`,
    :class:`EquationCollection` and more.
    """

    existing = []  # a list to store the created names

    def __init__(self, name=None):
        """Pick a name. Will increment the name if already used

        Args:
            name:
        """
        self.name = self.create_unique(name)

    def create_unique(self, name):
        """Check if name has already been used. If so, try to increment until
        not used

        Args:
            name:
        """
        if not name:
            return None
        i = 0
        key = name
        while key in self.existing:
            i += 1
            key = key.split("_")
            key = key[0] + "_{}".format(i)
        the_name = key
        self.existing.append(the_name)
        return the_name

    def __repr__(self):
        return str(self.name)


class UnitType(object):
    def __init__(self, n=None, m=None, comment=None):
        """
        Args:
            n (int): the UNIT number of the component. Allowable UNIT numbers
                are integers between 1 and n, where n is set in
                TrnsysConstants.f90 (default = 999).
            m (int): the TYPE number of the component. Allowable TYPE numbers
                are integers between 1 and 999.
            comment (str): Comment is an optional comment. The comment is
                reproduced on the output but is otherwise disregarded. Its
                function is primarily to help the user associate the UNIT and
                TYPE numbers with a particular component in the system.
        """
        self.Comment = comment
        self.n = n
        self.m = m

    def __repr__(self):
        """Overload __repr__() and str() to implement self._to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        return "UNIT {n} TYPE {m} {Comment}\n".format(n=self.n, m=self.m,
                                                      Comment=self.Comment)


class Parameters(object):
    def __init__(self, param_collection, n=None):
        """
        Args:
            param_collection (ParameterCollection): tuple of parameters
            n (int, optional): the number of PARAMETERS to follow on the next
                line(s). Typically this is the number of parameters required by
                the component, but may be less if more than one PARAMETERS
                statement is used for a given component.
        """
        self.v = param_collection
        if not n:
            self.n = self.v.size
        else:
            self.n = n

    def __repr__(self):
        """Overload __repr__() and str() to implement self._to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        head = "PARAMETERS {}\n".format(self.n)
        # loop through parameters and print the (value, name) tuples.
        v_ = ((self.v[param].value.m, "! {}".format(self.v.data[param].name))
              for param in self.v)
        params_str = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
        return head + params_str + "\n"


class Inputs(object):
    def __init__(self, input_collection, n=None):
        """
        Args:
            input_collection (InputCollection):
            n:
        """
        self.inputs = input_collection
        if not n:
            self.n = input_collection.size
        else:
            self.n = n

    def __repr__(self):
        """Overload __repr__() and str() to implement self._to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        head = "INPUTS {}\n".format(self.n)
        # "{u_i}, {o_i}": is an integer number referencing the number of the
        # UNIT to which the ith INPUT is connected. is an integer number
        # indicating to which OUTPUT (i.e., the 1st, 2nd, etc.) of UNIT
        # number ui the ith INPUT is connected.
        _ins = []
        for input in self.inputs.values():
            if input.is_connected:
                if isinstance(input.connected_to, TypeVariable):
                    _ins.append("{}, {}".format(
                        input.connected_to.model.unit_number,
                        input.connected_to.one_based_idx))
                else:
                    _ins.append(input.connected_to.name)
            else:
                _ins.append("0,0")
        core = "\t\t".join(_ins) + "\n"
        return str(head) + str(core)


class ExternalFiles(object):

    # todo: Implement DESIGNATE vs ASSIGN. See TRNSYS Manual, section 6.3.17.
    #  The DESIGNATE Statement and Logical Unit Numbers.

    def __init__(self, external_collection):
        """
        Args:
            external_collection (ExternalFileCollection):
        """
        self.external_files = external_collection

    def __repr__(self):
        """Overload __repr__() and str() to implement self._to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the external files (.dck)"""
        if self.external_files:
            head = "*** External files\n"
            v_ = (("ASSIGN", ext_file.value.normcase(), ext_file.logical_unit)
                  for ext_file in self.external_files.values())
            core = tabulate.tabulate(v_, tablefmt='plain', numalign="left")

            return str(head) + str(core)
        else:
            return ""


class Derivatives:
    # Todo: Implement Derivatives
    pass


class Trace:
    # Todo: Implement Trace
    pass


class Format:
    # Todo: Implement Format
    pass


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
                "with the equal sign")
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
        self.name = Name(name)
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
        return self.unit_number

    def update(self, E=None, **F):
        """D.update([E, ]**F) -> None.  Update D from dict/iterable E and F.
        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for k,
        v in E: D[k] = v
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (dict or Constant): The constant to add or update in D (self).
            F (dict or Constant): Other constants to update are passed.
        """
        if isinstance(E, Constant):
            _e = {E.name: E}
        else:
            for v in E.values():
                if not isinstance(v, Constant):
                    raise TypeError(
                        'Can only update an ConstantCollection with a'
                        'Constant, not a {}'.format(type(v)))
            _e = {v.name: v for v in E.values()}
            k: Constant
            _f = {v.name: v for k, v in F.values()}
            _e.update(_f)
        super().update(_e)

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
        v_ = ((equa.name, "=", str(equa))
              for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
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
        self.model = model
        self.is_connected = False

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
                "with the equal sign")
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
                'The expression does not have the same number of '
                'variables as arguments passed to the symbolic expression '
                'parser.')
        for i, arg in enumerate(
                sorted(exp.free_symbols, key=lambda sym: sym.name)):
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
    def unit_number(self):
        return self.model.unit_number

    def __repr__(self):
        return " = ".join([self.name, self._to_deck()])

    def __str__(self):
        return self.__repr__()

    def _to_deck(self):
        if isinstance(self.equals_to, TypeVariable):
            return "[{unit_number}, {output_id}]".format(
                unit_number=self.equals_to.model.unit_number,
                output_id=self.equals_to.one_based_idx)
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
        self.name = Name(name)
        self._unit = next(TrnsysModel.new_id)
        self.studio = StudioHeader.from_trnsysmodel(self)

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
        super().__setitem__(key, value)

    def update(self, E=None, **F):
        """D.update([E, ]**F) -> None.  Update D from dict/iterable E and F.
        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for k,
        v in E: D[k] = v
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (dict or Equation): The equation to add or update in D (self).
            F (dict or Equation): Other Equations to update are passed.
        """
        if isinstance(E, Equation):
            E.model = self
            _e = {E.name: E}
        else:
            for v in E.values():
                if not isinstance(v, Equation):
                    raise TypeError(
                        'Can only update an EquationCollection with an'
                        'Equation, not a {}'.format(type(v)))
            _e = {v.name: v for v in E.values()}
            k: Equation
            _f = {v.name: v for k, v in F.values()}
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
        v_ = ((equa.name, "=", equa._to_deck())
              for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
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
            (attr, self._meta[store][attr]) for attr in
            sorted(self._get_filtered_types(classe_, store),
                   key=lambda key: self._meta[store][key].order)
        )

    def _get_filtered_types(self, classe_, store):
        """
        Args:
            classe_:
            store:
        """
        return filter(
            lambda kv: isinstance(self._meta[store][kv], classe_),
            self._meta[store])


class ControlCards(object):
    """The :class:`ControlCards` is a container for all the TRNSYS Simulation
    Control Statements and Listing Control Statements. It implements the
    :func:`_to_deck` method which pretty-prints the statements with their
    docstrings.
    """

    def __init__(self, version=None, simulation=None, tolerances=None,
                 limits=None, nancheck=None, overwritecheck=None,
                 timereport=None, dfq=None, width=None, nocheck=None,
                 eqsolver=None, solver=None, nolist=None, list=None, map=None):
        """Each simulation must have SIMULATION and END statements. The other
        simulation control statements are optional. Default values are assumed
        for TOLERANCES, LIMITS, SOLVER, EQSOLVER and DFQ if they are not present

        Args:
            width:
            version (Version): The VERSION Statement. labels the deck with the
                TRNSYS version number. See :class:`Version` for more details.
            simulation (Simulation): The SIMULATION Statement.determines the
                starting and stopping times of the simulation as well as the
                time step to be used. See :class:`Simulation` for more details.
            tolerances (Tolerances, optional): Convergence Tolerances (
                TOLERANCES). Specifies the error tolerances to be used during a
                TRNSYS simulation. See :class:`Tolerances` for more details.
            limits (Limits, optional): The LIMITS Statement. Sets limits on the
                number of iterations that will be performed by TRNSYS during a
                time step before it is determined that the differential
                equations and/or algebraic equations are not converging. See
                :class:`Limits` for more details.
            nancheck (NaNCheck, optional): The NAN_CHECK Statement. An optional
                debugging feature in TRNSYS. If the NAN_CHECK statement is
                present, then the TRNSYS kernel checks every output of each
                component at each iteration and generates a clean error if ever
                one of those outputs has been set to the FORTRAN NaN condition.
                See :class:`NaNCheck` for more details.
            overwritecheck (OverwriteCheck, optional): The OVERWRITE_CHECK
                Statement. An optional debugging feature in TRNSYS. Checks to
                make sure that each Type did not write outside its allotted
                space. See :class:`OverwriteCheck` for more details.
            timereport (TimeReport, optional): The TIME_REPORT Statement. Turns
                on or off the internal calculation of the time spent on each
                unit. See :class:`TimeReport` for more details.
            dfq (DFQ, optional): Allows the user to select one of three
                algorithms built into TRNSYS to numerically solve differential
                equations. See :class:`DFQ` for more details.
            nocheck (NoCheck, optional): The Convergence Check Suppression
                Statement. Remove up to 20 inputs for the convergence check. See
                :class:`NoCheck` for more details.
            eqsolver (EqSolver, optional): The Equation Solving Method
                Statement. The order in which blocks of EQUATIONS are solved is
                controlled by the EQSOLVER statement. See :class:`EqSolver` for
                more details.
            solver (Solver, optional): The SOLVER Statement. Select the
                computational scheme. See :class:`Solver` for more details.
            nolist (NoList, optional): The NOLIST Statement. See :class:`NoList`
                for more details.
            list (List, optional): The LIST Statement. See :class:`List` for
                more details.
            map (Map, optional): The MAP Statement. See :class:`Map` for more
                details.

        Note:
            Some Statements have not been implemented because only TRNSYS 
            gods 😇
            use them. Here is a list of Statements that have been ignored:

            - The Convergence Promotion Statement (ACCELERATE)
            - The Calling Order Specification Statement (LOOP)
        """
        super().__init__()
        self.version = version
        self.simulation = simulation

        self.tolerances = tolerances
        self.limits = limits
        self.nancheck = nancheck
        self.overwritecheck = overwritecheck
        self.timereport = timereport

        self.dfq = dfq
        self.nocheck = nocheck
        self.eqsolver = eqsolver
        self.solver = solver

        # Listing Control Statements
        self.nolist = nolist
        self.list = list
        self.map = map

        self.end = End()

    @classmethod
    def all(cls):
        """Returns a SimulationCard with all available Statements initialized
        with their default values. This class method is not recommended since
        many of the Statements are a time consuming process and should be used
        as a debugging tool.
        """
        return cls(Version(), Simulation(), Tolerances(), Limits(), NaNCheck(),
                   OverwriteCheck(), TimeReport(), DFQ(), Width(), NoCheck(),
                   EqSolver(), Solver(), NoList(), List(), Map())

    @classmethod
    def debug_template(cls):
        """Returns a SimulationCard with useful debugging Statements."""
        return cls(Version(), Simulation(), map=Map(), nancheck=NaNCheck(),
                   overwritecheck=OverwriteCheck())

    @classmethod
    def basic_template(cls):
        """Returns a SimulationCard with only the required Statements"""
        return cls(Version(), Simulation())

    def _to_deck(self):
        """Creates a string representation. If the :attr:`doc` where specified,
        a small description is printed in comments
        """
        head = "*** Control Cards\n"
        v_ = ((str(param), "! {}".format(
            param.doc))
              for param in self.__dict__.values() if hasattr(param, 'doc'))
        statements = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
        return str(head) + str(statements)

    def set_statement(self, statement):
        self.__setattr__(statement.__class__.__name__.lower(), statement)


__statements__ = ['']


class Deck(object):
    """"""

    def __init__(self, name, control_card):
        self.models = ComponentCollection()
        self.control_card = control_card
        self.name = name

    @classmethod
    def from_file(cls, file, proforma_root=None):
        file = Path(file)
        with open(file) as dcklines:
            dck = cls(name=file.basename, control_card=None)
            cc = ControlCards()
            dck._control_card = cc
            line = dcklines.readline()
            iteration = 0
            maxiter = 26
            while line:
                iteration += 1
                # at each line check for a match with a regex
                line = cls._parse_logic(cc, dck, dcklines, line, proforma_root)

                if iteration < maxiter:
                    dcklines.seek(0)
                    line = '\n'

        # assert missing types
        # todo: list types that could not be parsed
        return dck

    @property
    def graph(self):
        import networkx as nx
        G = nx.MultiDiGraph()
        for component in self.models:
            G.add_node(component.unit_number, model=component,
                       pos=component.centroid)
            try:
                for output, typevar in component.inputs.items():
                    if typevar.is_connected:
                        u = component
                        v = typevar.connected_to.model
                        G.add_edge(u.unit_number, v.unit_number, key=output,
                                   from_model=u, to_model=v)
            except:
                pass
        return G

    def update_with_model(self, model):
        # iterate over models
        if model.unit_number in [mod.unit_number for mod in self.models]:
            for i, item in enumerate(self.models):
                if item.unit_number == model.unit_number:
                    self.models.pop(i)
                    break
        # in any case, add new one
        self.models.append(model)

    @classmethod
    def _parse_logic(cls, cc, dck, dcklines, line, proforma_root):
        while line:
            key, match = dck._parse_line(line)
            if key == 'version':
                version = match.group('version')
                v_ = Version.from_string(version.strip())
                cc.set_statement(v_)
            # identify a ConstantCollection
            if key == 'constants':
                n_cnts = match.group(key)
                cb = ConstantCollection()
                for n in range(int(n_cnts)):
                    line = next(dcklines)
                    cb.update(Constant.from_expression(line))
                cc.set_statement(cb)
            if key == 'simulation':
                sss = match.group(key)
                s_ = Simulation(*map(Constant, sss.split()))
                repr(s_.start)
                cc.set_statement(s_)
            if key == 'tolerances':
                sss = match.group(key)
                t_ = Tolerances(*(map(float, map(str.strip, sss.split()))))
                cc.set_statement(t_)
            if key == 'limits':
                sss = match.group(key)
                l_ = Limits(*(map(int, map(str.strip, sss.split()))))
                cc.set_statement(l_)
            if key == 'dfq':
                k = match.group(key)
                cc.set_statement(DFQ(k.strip()))
            if key == 'width':
                w = match.group(key)
                # todo: Implement Width
            if key == 'list':
                k = match.group(key)
                cc.set_statement(List(*k.strip().split()))
            if key == 'solver':
                k = match.group(key)
                cc.set_statement(Solver(*k.strip().split()))
            if key == 'nancheck':
                k = match.group(key)
                cc.set_statement(NaNCheck(*k.strip().split()))
            if key == 'overwritecheck':
                k = match.group(key)
                cc.set_statement(OverwriteCheck(*k.strip().split()))
            if key == 'timereport':
                k = match.group(key)
                cc.set_statement(TimeReport(*k.strip().split()))
            if key == 'eqsolver':
                k = match.group(key)
                cc.set_statement(EqSolver(*k.strip().split()))
            if key == 'userconstants':
                line = dcklines.readline()
                key, match = dck._parse_line(line)
            # identify an equation block (EquationCollection)
            if key == 'equations':
                # extract number of line, number of equations
                n_equations = match.group('equations')
                # read each line of the table until a blank line
                list_eq = []
                for line in [next(dcklines) for x in range(int(n_equations))]:
                    # extract number and value
                    value = line.strip()
                    # create equation
                    list_eq.append(Equation.from_expression(value))
                ec = EquationCollection(list_eq)
                ec._unit = 1
                #dck.update_with_model(ec)
                # append the dictionary to the data list
            # read studio markup
            if key == 'unitnumber':
                unit_number = match.group(key)
                ec._unit = int(unit_number)
                dck.update_with_model(ec)
            if key == 'unitname':
                unit_name = match.group(key)
                ec.name = unit_name
            if key == 'layer':
                layer = match.group(key)
                ec.change_component_layer(layer)
            if key == 'position':
                pos = match.group(key)
                ec.set_canvas_position(map(float, pos.strip().split()), False)
            # identify a unit (TrnsysModel)
            if key == 'unit':
                # extract unit_number, type_number and name
                u = match.group('unitnumber').strip()
                t = match.group('typenumber').strip()
                n = match.group('name').strip()

                _meta = MetaData(type=t)
                model = TrnsysModel(_meta, name=n)
                model._unit = int(u)
                dck.update_with_model(model)
                # read studio markup
                cls.unit_studio_markup(dck, dcklines, key,
                                       line, match, model,
                                       proforma_root)

            if key == 'parameters' or key == 'inputs':
                if model._meta.variables:
                    n_vars = int(match.group(key).strip())
                    i = -1
                    while line:
                        i += 1
                        line = dcklines.readline()
                        if not line.strip():
                            line = "\n"
                            i -= 1
                        else:
                            varkey, match = dck._parse_line(line)
                            if varkey == 'typevariable':
                                tvar = match.group('typevariable').strip()
                                try:
                                    other = cls.get_typevariable(dck, i,
                                                                 model,
                                                                 tvar, key)
                                except Exception as e:
                                    line = cls._parse_logic(cc, dck, dcklines,
                                                            line, proforma_root)
                            if i == n_vars - 1:
                                line = None
            # identify linkstyles
            if key == 'link':
                # identify u,v unit numbers
                u, v = match.group(key).strip().split(':')

                line = dcklines.readline()
                key, match = dck._parse_line(line)

                # identify linkstyle attributes
                if key == "linkstyle":
                    try:
                        _lns = match.groupdict()
                        path = _lns["path"].strip().split(":")

                        mapping = AnchorPoint(
                            dck.models.iloc[
                                int(u)]).studio_anchor_reverse_mapping

                        def find_closest(mappinglist, coordinate):
                            def distance(a, b):
                                a_ = Point(a)
                                b_ = Point(b)
                                return a_.distance(b_)

                            return min(mappinglist, key=lambda x: distance(x,
                                                                           coordinate))

                        u_coords = (int(_lns['u1']), int(_lns['u2']))
                        v_coords = (int(_lns['v1']), int(_lns['v2']))
                        loc = mapping[find_closest(mapping.keys(), u_coords)], \
                              mapping[find_closest(mapping.keys(), v_coords)]
                        color = get_rgb_from_int(int(_lns['color']))
                        linestyle = _studio_to_linestyle(int(_lns['linestyle']))
                        linewidth = int(_lns['linewidth'])

                        path = LineString(
                            [list(map(int, p.split(","))) for p in path])

                        dck.models.iloc[int(u)].set_link_style(
                            dck.models.iloc[int(v)],
                            loc, color, linestyle,
                            linewidth, path)
                    except:
                        pass

            line = dcklines.readline()
        return line

    @classmethod
    def get_typevariable(cls, dck, i, model, tvar, key):
        try:
            tvar = float(tvar)
        except:
            # deal with a string, either a Constant or a "[u, n]"
            if "," in tvar:
                unit_number, output_number = \
                    map(int, tvar.split(','))
                other = dck.models.iloc[unit_number]
                other.connect_to(model, mapping={
                    output_number - 1: i})
                return other
            else:
                if any((tvar in n.outputs) for n in dck.models):
                    # one Equation or Constant has this tvar
                    other = next((n for n in dck.models
                                  if (tvar in n.outputs)), None)
                    getattr(model, key)[i] = other[tvar]
                return None
        else:
            getattr(model, key)[i] = tvar
            return tvar

    @staticmethod
    def unit_studio_markup(dck, dcklines, key, line, match, model,
                           proforma_root):
        for line in [next(dcklines) for x in range(4)]:
            key, match = dck._parse_line(line)
            if key == 'unitname':
                pass
                # actual don't use this unit name since it was parsed earlier
                # unit_name = match.group(key)
                # model.name = unit_name
            if key == 'layer':
                layer = match.group(key)
                model.change_component_layer(layer)
            if key == 'position':
                pos = match.group(key)
                model.set_canvas_position(
                    map(float, pos.strip().split()), False)
            if key == 'model':
                _mod = match.group('model')
                tmf = Path(_mod.replace("\\", "/"))
                tmf_basename = tmf.basename()
                try:
                    inter_model = TrnsysModel.from_xml(tmf)
                except:
                    # replace extension with ".xml" and retry
                    xml_basename = tmf_basename.stripext() + ".xml"
                    proforma_root = Path(proforma_root)
                    if proforma_root is None:
                        proforma_root = Path.getcwd()
                    xmls = proforma_root.glob('*.xml')
                    xml = next((x for x in xmls if x.basename() ==
                                xml_basename), None)
                    if not xml:
                        msg = 'The proforma {} could not be found ' \
                              'at' \
                              ' "{}"'.format(xml_basename,
                                             proforma_root)
                        lg.warning(msg)
                        continue
                    inter_model = TrnsysModel.from_xml(xml)
                model.update_meta(inter_model._meta)

    def _parse_line(self, line):
        """
        Do a regex search against all defined regexes and
        return the key and match result of the first matching regex

        """

        for key, rx in self._setup_re().items():
            match = rx.search(line)
            if match:
                return key, match
        # if there are no matches
        return None, None

    def _setup_re(self):
        # set up regular expressions
        # use https://regexper.com to visualise these if required
        rx_dict = {
            'version': re.compile(
                r'(?i)(?P<key>^version)(?P<version>.*?)(?=(?:!|\\n|$))'),
            'constants': re.compile(
                r'(?i)(?P<key>^constants)(?P<constants>.*?)(?=(?:!|\\n|$))'),
            'simulation': re.compile(r'(?i)(?P<key>^simulation)('
                                     r'?P<simulation>.*?)(?=(?:!|$))'),
            'tolerances': re.compile(r'(?i)(?P<key>^tolerances)('
                                     r'?P<tolerances>.*?)(?=('
                                     r'?:!|$))'),
            'limits': re.compile(r'(?i)(?P<key>^limits)(?P<limits>.*?)(?=('
                                 r'?:!|$))'),
            'dfq': re.compile(r'(?i)(?P<key>^dfq)(?P<dfq>.*?)(?=(?:!|$))'),
            'width': re.compile(r'(?i)(?P<key>^width)(?P<width>.*?)(?=('
                                r'?:!|$))'),
            'list': re.compile(r'(?i)(?P<key>^list)(?P<list>.*?)(?=('
                               r'?:!|$))'),
            'solver': re.compile(r'(?i)(?P<key>^solver)(?P<solver>.*?)(?=('
                                 r'?:!|$))'),
            'nancheck': re.compile(
                r'(?i)(?P<key>^nan_check)(?P<nancheck>.*?)(?=('
                r'?:!|$))'),
            'overwritecheck': re.compile(
                r'(?i)(?P<key>^overwrite_check)(?P<overwritecheck>.*?)(?=('
                r'?:!|$))'),
            'timereport': re.compile(
                r'(?i)(?P<key>^time_report)(?P<timereport>.*?)(?=('
                r'?:!|$))'),
            'eqsolver': re.compile(
                r'(?i)(?P<key>^eqsolver)(?P<eqsolver>.*?)(?=('
                r'?:!|$))'),
            'equations': re.compile(
                r'(?i)(?P<key>^equations)(?P<equations>.*?)(?=(?:!|$))'),
            'unitnumber': re.compile(r'(?i)(?P<key>^\*\$unit_number)('
                                     r'?P<unitnumber>.*?)(?=(?:!|$))'),
            'unitname': re.compile(
                r'(?i)(?P<key>^\*\$unit_name)(?P<unitname>.*?)(?=(?:!|$))'),
            'layer': re.compile(
                r'(?i)(?P<key>^\*\$layer)(?P<layer>.*?)(?=(?:!|$))'),
            'position': re.compile(
                r'(?i)(?P<key>^\*\$position)(?P<position>.*?)(?=(?:!|$))'),
            'unit': re.compile(
                r'(?i)(^unit)(?P<unitnumber>.*?)(type)(?P<typenumber>.*\s)('
                r'?P<name>\s.*?)('
                r'?=(?:!|$))'),
            'model': re.compile(r'(?i)(?P<key>^\*\$model)(?P<model>.*?)(?=('
                                r'?:!|$))'),
            'link': re.compile(r'(?i)(^\*!link\s)(?P<link>.*?)(?=(?:!|$))'),
            'linkstyle': re.compile(
                r'(?i)(?:^\*!connection_set )(?P<u1>.*?):(?P<u2>.*?):('
                r'?P<v1>.*?):(?P<v2>.*?):(?P<order>.*?):(?P<color>.*?):('
                r'?P<linestyle>.*?):(?P<linewidth>.*?):(?P<ignored>.*?):('
                r'?P<path>.*?$)'),
            'userconstants': re.compile(r'(?i)(?P<key>^\*\$user_constants)('
                                        r'?=(?:!|$))'),
            'parameters': re.compile(
                r'(?i)(?P<key>^parameters)(?P<parameters>.*?)(?=(?:!|$))'),
            'inputs': re.compile(
                r'(?i)(?P<key>^inputs)(?P<inputs>.*?)(?=(?:!|$))'),
            'typevariable': re.compile(
                r'^(?![*$!\s])(?P<typevariable>.*?)(?=(?:!|$))'),
        }
        return rx_dict
