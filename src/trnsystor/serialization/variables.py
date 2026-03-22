"""Serializers for TypeVariable collections."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tabulate as _tabulate

if TYPE_CHECKING:
    from trnsystor.collections.derivatives import DerivativesCollection
    from trnsystor.collections.externalfile import ExternalFileCollection
    from trnsystor.collections.initialinputvalues import InitialInputValuesCollection
    from trnsystor.collections.input import InputCollection
    from trnsystor.collections.parameter import ParameterCollection
    from trnsystor.collections.specialcards import SpecialCardsCollection


def serialize_parameters(obj: ParameterCollection) -> str:
    """Return deck representation of ParameterCollection."""
    from trnsystor.quantity import Quantity
    from trnsystor.statement import Equation

    head = f"PARAMETERS {obj.size}\n"
    v_ = []
    for param in obj.values():
        if not param._is_question:
            if isinstance(param.value, Equation):
                v_.append(
                    (
                        param.value.name,
                        f"! {param.one_based_idx} {param.name}",
                    )
                )
            elif isinstance(param.value, Quantity):
                v_.append(
                    (
                        param.value.m,
                        f"! {param.one_based_idx} {param.name}",
                    )
                )
            else:
                model_name = (
                    param.model.name if param.model is not None else "<unknown>"
                )
                raise NotImplementedError(
                    f"Printing parameter '{param.name}' of type "
                    f"'{type(param.value)}' from unit "
                    f"'{model_name}' is not supported"
                )
    params_str = _tabulate.tabulate(v_, tablefmt="plain", numalign="left")
    return head + params_str + "\n"


def serialize_inputs(obj: InputCollection) -> str:
    """Return deck representation of InputCollection."""
    from trnsystor.statement import Constant, Equation
    from trnsystor.typevariable import TypeVariable

    if obj.size == 0:
        return ""

    head = f"INPUTS {obj.size}\n"
    _ins = []
    for input in obj.values():
        if input.is_connected:
            if isinstance(input.predecessor, Equation | Constant):
                _ins.append(
                    (
                        input.predecessor.name,
                        _input_help_text(input),
                    )
                )
            elif isinstance(input.predecessor, TypeVariable):
                pred_model = input.predecessor._require_model()
                _ins.append(
                    (
                        f"{pred_model.unit_number},{input.predecessor.one_based_idx}",
                        _input_help_text(input),
                    )
                )
            else:
                raise NotImplementedError(
                    f"With unit {input.model.name}, printing input "
                    f"'{input.name}' connected with output of "
                    f"type '{type(input.connected_to)}' from unit "
                    f"'{input.connected_to.model.name}' is not supported"
                )
        else:
            _ins.append(
                (
                    "0,0",
                    f"! [unconnected] {input.model.name}:{input.name}",
                )
            )
    core = _tabulate.tabulate(_ins, tablefmt="plain", numalign="left")
    return str(head) + core + "\n"


def _input_help_text(input_type) -> str:
    """Generate help text for input connection."""
    return (
        f"! {input_type.predecessor.model.name}:"
        f"{input_type.predecessor.name} -> "
        f"{input_type.model.name}:{input_type.name}"
    )


def serialize_initial_input_values(obj: InitialInputValuesCollection) -> str:
    """Return deck representation of InitialInputValuesCollection."""
    from trnsystor.quantity import Quantity

    if obj.size == 0:
        return ""

    head = "*** INITIAL INPUT VALUES\n"
    input_tuples = [
        (
            v.value.m if isinstance(v.value, Quantity) else v.value,
            f"! {v.name}",
        )
        for v in obj.values()
    ]
    core = _tabulate.tabulate(input_tuples, tablefmt="plain", numalign="left")
    return head + core + "\n"


def serialize_derivatives(obj: DerivativesCollection) -> str:
    """Return deck representation of DerivativesCollection."""
    if obj.size == 0:
        return ""

    head = f"DERIVATIVES {obj.size}\n"
    _ins = [(derivative.value.m, f"! {derivative.name}") for derivative in obj.values()]
    core = _tabulate.tabulate(_ins, tablefmt="plain", numalign="left")
    return head + core + "\n"


def serialize_external_files(obj: ExternalFileCollection) -> str:
    """Return deck representation of ExternalFileCollection."""
    if obj:
        head = "*** External files\n"
        v_ = (
            ("ASSIGN", f'"{ext_file.value}"', ext_file.logical_unit)
            for ext_file in obj.values()
        )
        core = _tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return str(head) + str(core)
    else:
        return ""


def serialize_special_cards(obj: SpecialCardsCollection) -> str:
    """Return deck representation of SpecialCardsCollection."""
    if obj.size == 0:
        return ""

    _ins = [[" ".join(a for a in [sc.name, sc.default] if a)] for sc in obj]
    core = _tabulate.tabulate(_ins, tablefmt="plain")
    return core
