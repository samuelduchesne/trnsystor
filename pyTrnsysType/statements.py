class Statement(object):
    """This is the base class for many of the TRNSYS Simulation Control and
    Listing Control Statements. It implements common methods such as the repr()
    method.
    """

    def __init__(self, doc=""):
        self.doc = doc

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
        self.n = n
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
        self.n = n
        self.doc = "The OVERWRITE_CHECK Statement"

    def _to_deck(self):
        return "OVERWRITE_CHECK {}".format(self.n)


class TimeReport(Statement):
    """The statement TIME_REPORT turns on or off the internal calculation of the
    time spent on each unit. If this feature is desired, the listing file will
    contain this information at the end of the file.
    """

    # Todo: Implement the TimeReport Statement

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


class Constants(Statement):
    """The CONSTANTS statement is useful when simulating a number of systems
    with identical component configurations but with different parameter values,
    initial input values, or initial values of time dependent variables.
    """

    # Todo: Finish the Constants Statement

    def __init__(self, constants=None):
        """Initialize a Constants object.

        Args:
            constants (ConstantCollection or list of ConstantCollection):
        """
        super().__init__()
        self.constants = constants
        self.doc = "The CONSTANTS Statement"

    def _to_deck(self):
        return "CONSTANTS 0" if not self.constants else "todo"


class Equations(Statement):
    """The EQUATIONS statement allows variables to be defined as algebraic
    functions of constants, previously defined variables, and outputs from
    TRNSYS components. These variables can then be used in place of numbers in
    the TRNSYS input file to represent inputs to components; numerical values of
    parameters; and initial values of inputs and time-dependent variables.
    """

    # Todo: Finish the Equations Statement

    def __init__(self, equations=None):
        """Initialize an Equations object.

        Args:
            equations (EquationCollection or list of EquationCollection,
                optional):
        """
        super().__init__()
        self.equations = equations
        self.doc = "The EQUATIONS Statement"

    def _to_deck(self):
        return "EQUATIONS 0" if not self.equations else "todo"


class List(Statement):
    """The LIST statement is used to turn on the TRNSYS processor listing
    after it has been turned off by a NOLIST statement."""

    # Todo: Implement the List Statement

    def __init__(self, activate=False):
        """
        Hint:
            The listing is assumed to be on at the beginning of a TRNSYS
            input file. As many LIST cards as desired may appear in a TRNSYS
            input file and may be located anywhere in the input file.

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
        """Initialize the The Differential Equation Solving Method Statement

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
            raise ValueError("TRNSYS allows only up to 20 different INPUTS to "
                             "be removed")
        self.inputs = inputs
        self.doc = "CHECK Statement"

    def _to_deck(self):
        head = "NOCHECK {}\n".format(len(self.inputs))
        core = "\t".join(
            ["{}, {}".format(
                input.model.unit_number,
                input.one_based_idx)
                for input in self.inputs])
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
    signals the TRNSYS processor that no more control statements follow and
    that the simulation may begin."""

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
        self.doc = "Solver statement\tMinimum relaxation factor\tMaximum " \
                   "relaxation factor"

    def _to_deck(self):
        return "SOLVER {} {} {}".format(self.k, self.rf_min, self.rf_max) \
            if self.k == 0 else "SOLVER {}".format(self.k)
