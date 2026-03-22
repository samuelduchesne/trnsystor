"""Serializers for TrnsysModel, EquationCollection, and ConstantCollection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tabulate as _tabulate

if TYPE_CHECKING:
    from trnsystor.collections.constant import ConstantCollection
    from trnsystor.collections.equation import EquationCollection
    from trnsystor.trnsysmodel import TrnsysModel


def serialize_trnsys_model(obj: TrnsysModel) -> str:
    """Return deck representation of TrnsysModel."""
    unit_type = f"UNIT {obj.unit_number} TYPE  {obj.type_number} {obj.name}\n"
    studio = obj.studio
    params = obj.parameters
    inputs = obj.inputs
    initial_input_values = obj.initial_input_values
    special_cards = obj.special_cards
    derivatives = obj.derivatives
    externals = obj.external_files

    return (
        str(unit_type)
        + str(studio)
        + str(params)
        + str(inputs)
        + str(initial_input_values)
        + str(special_cards)
        + str(derivatives)
        + str(externals)
    )


def serialize_equation_collection(obj: EquationCollection) -> str:
    """Return deck representation of EquationCollection."""
    header_comment = f'* EQUATIONS "{obj.name}"\n*\n'
    head = f"EQUATIONS {len(obj)}\n"
    v_ = ((equa.name, "=", equa._to_deck()) for equa in obj.values())
    core = _tabulate.tabulate(v_, tablefmt="plain", numalign="left")

    unit_name = f"*$UNIT_NAME {obj.unit_name}"
    layer = "*$LAYER {}".format(" ".join(obj.studio.layer))
    position = f"*$POSITION {obj.studio.position.x} {obj.studio.position.y}"
    unit_number = f"*$UNIT_NUMBER {obj.unit_number}"
    tail = "\n" + "\n".join([unit_name, layer, position, unit_number]) + "\n"

    return str(header_comment) + str(head) + str(core) + str(tail)


def serialize_constant_collection(obj: ConstantCollection) -> str:
    """Return deck representation of ConstantCollection."""
    header_comment = f'* CONSTANTS "{obj.name}"\n\n'
    head = f"CONSTANTS {len(obj)}\n"
    v_ = ((equa.name, "=", str(equa)) for equa in obj.values())
    core = _tabulate.tabulate(v_, tablefmt="plain", numalign="left")
    return str(header_comment) + str(head) + str(core)
