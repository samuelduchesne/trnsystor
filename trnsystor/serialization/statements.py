"""Serializers for Statement subclasses and ControlCards."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tabulate as _tabulate

if TYPE_CHECKING:
    from trnsystor.controlcards import ControlCards
    from trnsystor.statement.constant import Constant
    from trnsystor.statement.dfq import DFQ
    from trnsystor.statement.end import End
    from trnsystor.statement.eqsolver import EqSolver
    from trnsystor.statement.equation import Equation
    from trnsystor.statement.limites import Limits
    from trnsystor.statement.map import Map
    from trnsystor.statement.nancheck import NaNCheck
    from trnsystor.statement.nocheck import NoCheck
    from trnsystor.statement.nolist import NoList
    from trnsystor.statement.overwritecheck import OverwriteCheck
    from trnsystor.statement.simulation import Simulation
    from trnsystor.statement.solver import Solver
    from trnsystor.statement.statement import Statement
    from trnsystor.statement.timereport import TimeReport
    from trnsystor.statement.tolerances import Tolerances
    from trnsystor.statement.version import Version
    from trnsystor.statement.width import Width


def serialize_statement(obj: Statement) -> str:
    """Base Statement serializer — returns empty string."""
    return ""


def serialize_simulation(obj: Simulation) -> str:
    """Return deck representation of Simulation."""
    return f"SIMULATION {obj.start} {obj.stop} {obj.step}"


def serialize_version(obj: Version) -> str:
    """Return deck representation of Version."""
    return "VERSION {}".format(".".join(map(str, obj.v)))


def serialize_tolerances(obj: Tolerances) -> str:
    """Return deck representation of Tolerances."""
    return str(f"TOLERANCES {obj.epsilon_d} {obj.epsilon_a}")


def serialize_limits(obj: Limits) -> str:
    """Return deck representation of Limits."""
    return str(f"LIMITS {obj.m} {obj.n} {obj.p}")


def serialize_dfq(obj: DFQ) -> str:
    """Return deck representation of DFQ."""
    return str(f"DFQ {obj.k}")


def serialize_width(obj: Width) -> str:
    """Return deck representation of Width."""
    return str(f"WIDTH {obj.k}")


def serialize_solver(obj: Solver) -> str:
    """Return deck representation of Solver."""
    return (
        f"SOLVER {obj.k} {obj.rf_min} {obj.rf_max}" if obj.k == 0 else f"SOLVER {obj.k}"
    )


def serialize_nancheck(obj: NaNCheck) -> str:
    """Return deck representation of NaNCheck."""
    return f"NAN_CHECK {obj.n}"


def serialize_overwritecheck(obj: OverwriteCheck) -> str:
    """Return deck representation of OverwriteCheck."""
    return f"OVERWRITE_CHECK {obj.n}"


def serialize_timereport(obj: TimeReport) -> str:
    """Return deck representation of TimeReport."""
    return f"TIME_REPORT {obj.n}"


def serialize_eqsolver(obj: EqSolver) -> str:
    """Return deck representation of EqSolver."""
    return f"EQSOLVER {obj.n}"


def serialize_end(obj: End) -> str:
    """Return deck representation of End."""
    return "END"


def serialize_nolist(obj: NoList) -> str:
    """Return deck representation of NoList."""
    return "NOLIST" if obj.active else ""


def serialize_nocheck(obj: NoCheck) -> str:
    """Return deck representation of NoCheck."""
    head = f"NOCHECK {len(obj.inputs)}\n"
    core = "\t".join(
        [f"{input.model.unit_number}, {input.one_based_idx}" for input in obj.inputs]
    )
    return str(head) + str(core)


def serialize_map(obj: Map) -> str:
    """Return deck representation of Map."""
    return "MAP" if obj.active else ""


def serialize_constant_statement(obj: Constant) -> str:
    """Return deck representation of Constant statement."""
    return str(obj.equals_to) if obj.equals_to is not None else ""


def serialize_equation_statement(obj: Equation) -> str:
    """Return deck representation of Equation statement."""
    from sympy import Expr

    from trnsystor.typevariable import TypeVariable
    from trnsystor.utils import print_my_latex

    if isinstance(obj.equals_to, TypeVariable):
        tv_model = obj.equals_to._require_model()
        unit = tv_model.unit_number
        idx = obj.equals_to.one_based_idx
        return f"[{unit}, {idx}]"
    elif isinstance(obj.equals_to, Expr):
        return print_my_latex(obj.equals_to)
    else:
        return str(obj.equals_to) if obj.equals_to is not None else ""


def serialize_control_cards(obj: ControlCards) -> str:
    """Return deck representation of ControlCards."""
    from trnsystor.component import Component
    from trnsystor.statement.version import Version

    version = str(obj.version) + "\n"
    head = "*** Control Cards\n"
    v_ = []
    for param in obj.__dict__.values():
        if isinstance(param, Version):
            continue
        if isinstance(param, Component):
            v_.append((str(param), None))
        if hasattr(param, "doc"):
            v_.append((str(param), f"! {getattr(param, 'doc', '')}"))
        else:
            pass
    statements = _tabulate.tabulate(tuple(v_), tablefmt="plain", numalign="left")
    return version + head + statements
