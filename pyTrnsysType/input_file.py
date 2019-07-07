import collections
import itertools

import tabulate

from pyTrnsysType import TypeVariable, TrnsysModel
from pyTrnsysType.statements import Version, NaNCheck, OverwriteCheck, \
    TimeReport, Constants, Equations, List, Simulation, Tolerances, Limits, \
    DFQ, \
    NoCheck, NoList, Map, EqSolver, End, Solver
from .trnsymodel import ParameterCollection, InputCollection, \
    ExternalFileCollection


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
        """Overload __repr__() and str() to implement self.to_deck()"""
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
        """Overload __repr__() and str() to implement self.to_deck()"""
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
        """Overload __repr__() and str() to implement self.to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        head = "INPUTS {}\n".format(self.n)
        # "{u_i}, {o_i}": is an integer number referencing the number of the
        # UNIT to which the ith INPUT is connected. is an integer number
        # indicating to which OUTPUT (i.e., the 1st, 2nd, etc.) of UNIT
        # number ui the ith INPUT is connected.
        core = "\t".join(
            ["{}, {}".format(
                input.connected_to.model.unit_number,
                input.connected_to.one_based_idx) if input.is_connected else
             "0, 0"
             for input in self.inputs.values()]) + "\n"
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
        """Overload __repr__() and str() to implement self.to_deck()"""
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


class Equation(object):
    """The EQUATIONS statement allows variables to be defined as algebraic
    functions of constants, previously defined variables, and outputs from
    TRNSYS components. These variables can then be used in place of numbers in
    the TRNSYS input file to represent inputs to components; numerical values of
    parameters; and initial values of inputs and time-dependent variables.
    """

    _new_id = itertools.count(start=1)

    def __init__(self, name=None, equals_to=None):
        """
        Args:
            name:
            equals_to:
        """
        self._n = next(self._new_id)
        self.name = name
        self.equals_to = equals_to

    @classmethod
    def from_expression(cls, expression):
        """Create an equation from a string expression. Anything before the
        equal sign ("=") will become a Constant and anything after will become
        the equality statement.

        Args:
            expression (str): A user-defined expression to parse
        """
        if "=" not in expression:
            raise ValueError(
                "The from_expression constructor must contain an expression "
                "with the equal sign")
        a, b = expression.split("=")
        return cls(a.strip(), b.strip())

    @property
    def number(self):
        """The equation number. Unique"""
        return self._n

    def to_deck(self):
        if isinstance(self.equals_to, TypeVariable):
            return "[{unit_number}, {output_id}]".format(
                unit_number=self.equals_to.model.unit_number,
                output_id=self.equals_to.one_based_idx)
        else:
            return self.equals_to


class EquationCollection(collections.UserList):

    def __init__(self, initlist=None, name=None):
        """Initialize a new EquationCollection.

        Example:
            >>> equa1 = Equation.from_expression("TdbAmb = [011,001]")
            >>> equa2 = Equation.from_expression("rhAmb = [011,007]")
            >>> EquationCollection([equa1, equa2])

        Args:
            initlist (Iterable, optional): An iterable.
            name (str): A user defined name for this collection of equations.
                This name will be used to identify this block of equations in
                the .dck file;
        """
        super(EquationCollection, self).__init__(initlist)
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
        return self.to_deck()

    def to_deck(self):
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
        v_ = ((equa.name, "=", equa.to_deck())
              for equa in self)
        core = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
        return str(header_comment) + str(head) + str(core)

    @property
    def size(self):
        return len(self)

    @property
    def unit_number(self):
        return self._unit


class ControlCards(object):
    """The :class:`ControlCards` is a container for all the TRNSYS Simulation
    Control Statements and Listing Control Statements. It implements the
    :func:`to_deck` method which pretty-prints the statements with their
    docstrings.
    """

    def __init__(self, version, simulation, tolerances=None, limits=None,
                 nancheck=None, overwritecheck=None, timereport=None,
                 constants=None, equations=None, dfq=None, nocheck=None,
                 eqsolver=None, solver=None, nolist=None, list=None, map=None):
        """Each simulation must have SIMULATION and END statements. The other
        simulation control statements are optional. Default values are assumed
        for TOLERANCES, LIMITS, SOLVER, EQSOLVER and DFQ if they are not present

        Args:
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
            constants (Constants, optional): The CONSTANTS Statement. See
                :class:`Constants` for more details.
            equations (Equations, optional): The EQUATIONS Statement. See
                :class:`Equations` for more details.
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
            Some Statements have not been implemented because only TRNSYS gods 😇
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

        self.equations = equations
        self.constants = constants

        self.end = End()

    @classmethod
    def all(cls):
        """Returns a SimulationCard with all available Statements initialized
        with their default values. This class method is not recommended since
        many of the Statements are a time consuming process and should be used
        as a debugging tool.
        """
        return cls(Version(), Simulation(), Tolerances(), Limits(), NaNCheck(),
                   OverwriteCheck(), TimeReport(), Constants(), Equations(),
                   DFQ(), NoCheck(), EqSolver(), Solver(), NoList(), List(),
                   Map())

    @classmethod
    def debug_template(cls):
        """Returns a SimulationCard with useful debugging Statements."""
        return cls(Version(), Simulation(), map=Map(), nancheck=NaNCheck(),
                   overwritecheck=OverwriteCheck())

    @classmethod
    def basic_template(cls):
        """Returns a SimulationCard with only the required Statements"""
        return cls(Version(), Simulation())

    def to_deck(self):
        head = "*** Control Cards\n"
        v_ = ((str(param), "! {}".format(
            param.doc))
              for param in self.__dict__.values() if param)
        statements = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
        return str(head) + str(statements)
