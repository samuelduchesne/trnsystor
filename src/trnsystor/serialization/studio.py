"""Serializer for StudioHeader."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trnsystor.studio import StudioHeader


def serialize_studio_header(obj: StudioHeader) -> str:
    """Return deck representation of StudioHeader."""
    unit_name = f"*$UNIT_NAME {obj.unit_name}"
    model = f"*$MODEL {obj.model.expanduser().resolve()}"
    position = f"*$POSITION {obj.position.x} {obj.position.y}"
    layer = "*$LAYER {}".format(" ".join(obj.layer))
    return "\n".join([unit_name, model, position, layer]) + "\n"
