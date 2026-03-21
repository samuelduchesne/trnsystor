"""Serializer for LinkStyle."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trnsystor.linkstyle import LinkStyle


def serialize_link_style(obj: LinkStyle) -> str:
    """Return deck representation of LinkStyle.

    Examples:
        0:20:40:20:1:0:0:0:1:513,441:471,441:471,430:447,430
    """
    from shapely.geometry import LineString

    from trnsystor.anchorpoint import AnchorPoint
    from trnsystor.linkstyle import _linestyle_to_studio, _to_rgb
    from trnsystor.utils import get_int_from_rgb

    u_anchor_name, v_anchor_name = obj.anchor_ids
    anchors = (
        ":".join(
            [
                ":".join(
                    map(
                        str,
                        AnchorPoint(obj.u).studio_anchor_mapping[u_anchor_name],
                    )
                ),
                ":".join(
                    map(
                        str,
                        AnchorPoint(obj.u).studio_anchor_mapping[v_anchor_name],
                    )
                ),
            ]
        )
        + ":"
    )

    rgb = _to_rgb(obj.get_color())
    color = (
        str(get_int_from_rgb(tuple(c * 255 for c in rgb)))
        + ":"
    )
    raw_path = obj.path
    if raw_path is None:
        coords = []
    elif isinstance(raw_path, LineString):
        coords = [
            tuple(int(v) for v in pt)
            for pt in raw_path.coords
        ]
    elif isinstance(raw_path, list):
        coords = [
            tuple(int(v) for v in pt)
            for pt in raw_path
        ]
    else:
        coords = []
    # Handle single-point case (flatten 1-d)
    if coords and not isinstance(coords[0], tuple | list):
        coords = [tuple(coords)]
    path = ",".join([":".join(map(str, pt)) for pt in coords])
    linestyle = str(_linestyle_to_studio(obj.get_linestyle())) + ":"
    linewidth = str(obj.get_linewidth()) + ":"
    connection_set = anchors + "1:" + color + linestyle + linewidth + "1:" + path
    head = f"*!LINK {obj.u.unit_number}:{obj.v.unit_number}\n"
    tail = f"*!CONNECTION_SET {connection_set}\n"
    return head + tail
