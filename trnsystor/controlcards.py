"""ControlCards module."""
from dataclasses import dataclass, field, fields

import tabulate

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


@dataclass
class ControlCards:
    """Container for TRNSYS control and listing statements.

    The order of the fields is significant since it defines the order in which
    the statements are written to the deck. An ``END`` statement is always
    appended at the end of the deck.
    """

    version: Version | None = None
    simulation: Simulation | None = None
    tolerances: Tolerances | None = None
    limits: Limits | None = None
    nancheck: NaNCheck | None = None
    overwritecheck: OverwriteCheck | None = None
    timereport: TimeReport | None = None
    dfq: DFQ | None = None
    width: Width | None = None
    nocheck: NoCheck | None = None
    eqsolver: EqSolver | None = None
    solver: Solver | None = None

    # Listing Control Statements
    nolist: NoList | None = None
    list: List | None = None
    map: Map | None = None

    end: End = field(default_factory=End, init=False)

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
        for field_ in fields(self):
            param = getattr(self, field_.name, None)
            if isinstance(param, Version) or param is None:
                continue
            if hasattr(param, "doc"):
                v_.append((str(param), f"! {param.doc}"))
            else:
                v_.append((str(param), None))
        statements = tabulate.tabulate(tuple(v_), tablefmt="plain", numalign="left")
        return version + head + statements

    def set_statement(self, statement):
        """Set `statement`."""
        self.__setattr__(statement.__class__.__name__.lower(), statement)
