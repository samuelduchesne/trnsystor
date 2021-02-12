"""ControlCards module."""
import tabulate

from trnsystor.component import Component
from trnsystor.statement import (
    DFQ,
    End,
    EqSolver,
    Limits,
    List,
    Map,
    NaNCheck,
    NoCheck,
    NoList,
    OverwriteCheck,
    Simulation,
    Solver,
    TimeReport,
    Tolerances,
    Version,
    Width,
)


class ControlCards(object):
    """ControlCards class.

    The :class:`ControlCards` is a container for all the TRNSYS Simulation
    Control Statements and Listing Control Statements. It implements the
    :func:`_to_deck` method which pretty-prints the statements with their
    docstrings.
    """

    def __init__(
        self,
        version=None,
        simulation=None,
        tolerances=None,
        limits=None,
        nancheck=None,
        overwritecheck=None,
        timereport=None,
        dfq=None,
        width=None,
        nocheck=None,
        eqsolver=None,
        solver=None,
        nolist=None,
        list=None,
        map=None,
    ):
        """Insure that each simulation has a SIMULATION and END statements.

        The other simulation control statements are optional. Default values are assumed
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
            dfq (DFQ, optional): Allows the user to select one of three
                algorithms built into TRNSYS to numerically solve differential
                equations. See :class:`DFQ` for more details.
            width (Width, optional): Set the number of characters to be allowed
                on a line of TRNSYS output. See :class:`Width` for more details.
            nocheck (NoCheck, optional): The Convergence Check Suppression
                Statement. Remove up to 20 inputs for the convergence check. See
                :class:`NoCheck` for more details.
            eqsolver (EqSolver, optional): The Equation Solving Method
                Statement. The order in which blocks of EQUATIONS are solved is
                controlled by the EQSOLVER Statement. See :class:`EqSolver` for
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

        self.end = End()

    def __str__(self):
        """Return str(self)."""
        return self.__repr__()

    def __repr__(self):
        """Return Deck representation of self."""
        return self._to_deck()

    @classmethod
    def all(cls):
        """Return a SimulationCard with all available Statements.

        If not initialized, default values are used. This class method is not
        recommended since many of the Statements are a time consuming process and
        should be used as a debugging tool.

        See Also:
            - :meth:`basic_template`
            - :meth:`debug_template`
        """
        return cls(
            Version(),
            Simulation(),
            Tolerances(),
            Limits(),
            NaNCheck(n=1),
            OverwriteCheck(n=1),
            TimeReport(n=1),
            DFQ(),
            Width(),
            NoCheck(),
            EqSolver(),
            Solver(),
            NoList(),
            List(activate=True),
            Map(activate=True),
        )

    @classmethod
    def debug_template(cls):
        """Return a SimulationCard with useful debugging Statements."""
        return cls(
            version=Version(),
            simulation=Simulation(),
            map=Map(activate=True),
            nancheck=NaNCheck(n=1),
            overwritecheck=OverwriteCheck(n=1),
        )

    @classmethod
    def basic_template(cls):
        """Return a SimulationCard with only the required Statements."""
        return cls(version=Version(), simulation=Simulation())

    def _to_deck(self):
        """Return deck representation of self.

        If the :attr:`doc` is specified, a small description is printed in comments.
        """
        version = str(self.version) + "\n"
        head = "*** Control Cards\n"
        v_ = []
        for param in self.__dict__.values():
            if isinstance(param, Version):
                continue
            if isinstance(param, Component):
                v_.append((str(param), None))
            if hasattr(param, "doc"):
                v_.append((str(param), "! {}".format(param.doc)))
            else:
                pass
        statements = tabulate.tabulate(tuple(v_), tablefmt="plain", numalign="left")
        return version + head + statements

    def set_statement(self, statement):
        """Set `statement`."""
        self.__setattr__(statement.__class__.__name__.lower(), statement)
