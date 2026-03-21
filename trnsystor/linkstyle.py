"""LinkStyle module."""

from shapely.geometry import LineString

from trnsystor.anchorpoint import AnchorPoint
from trnsystor.utils import get_int_from_rgb, redistribute_vertices

# Minimal named color table (CSS3 subset most commonly used in TRNSYS Studio).
_NAMED_COLORS = {
    "black": (0.0, 0.0, 0.0),
    "white": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 0.5, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "orange": (1.0, 0.647, 0.0),
    "gray": (0.502, 0.502, 0.502),
    "grey": (0.502, 0.502, 0.502),
}


def _to_rgb(color):
    """Convert a color specification to an (r, g, b) tuple with values in [0, 1].

    Supports hex strings (#RRGGBB), named colors, and RGB/RGBA tuples.
    """
    if isinstance(color, tuple | list):
        return tuple(float(c) for c in color[:3])
    if isinstance(color, str):
        color = color.strip().lower()
        if color.startswith("#"):
            h = color.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
        if color in _NAMED_COLORS:
            return _NAMED_COLORS[color]
        # Try as a grayscale float string (e.g. '0.8')
        try:
            g = float(color)
            return (g, g, g)
        except ValueError:
            pass
    raise ValueError(f"Unrecognized color: {color!r}")


class LinkStyle:
    """LinkStyle class."""

    def __init__(
        self,
        u,
        v,
        loc,
        color="black",
        linestyle="-",
        linewidth=None,
        path=None,
        autopath=True,
    ):
        """Initialize class.

        Args:
            u (Component): from Model.
            v (Component): to Model.
            loc (str or tuple): loc (str): The location of the anchor. The
                strings 'top-left', 'top-right', 'bottom-left', 'bottom-right'
                place the anchor point at the corresponding corner of the
                :class:`TrnsysModel`. The strings 'top-center', 'center-right',
                'bottom-center', 'center-left' place the anchor point at the
                edge of the corresponding :class:`TrnsysModel`. The string
                'best' places the anchor point at the location, among the eight
                locations defined so far, with the shortest distance with the
                destination :class:`TrnsysModel` (other). The location can also
                be a 2-tuple giving the coordinates of the origin
                :class:`TrnsysModel` and the destination :class:`TrnsysModel`.
            color (str or tuple): The color of the line. Accepts hex strings
                ('#008000'), named colors ('green', 'black'), RGB tuples
                ((0,1,0)), or grayscale strings ('0.8').
            linestyle (str): Possible values: '-' or 'solid', '--' or 'dashed',
                '-.' or 'dashdot', ':' or 'dotted', '-.' or 'dashdotdot'.
            linewidth (float): The link line width in points.
            path (LineString or MultiLineString): The path the link should
                follow.
            autopath (bool): If True, find best path.
        """
        self.u = u
        self.v = v
        self.loc = loc
        self._color = color
        self._linestyle = linestyle
        self._linewidth = linewidth
        self.autopath = autopath
        self._path = None

    @property
    def path(self):
        """Return the path of self."""
        if self._path is None:
            u_anchor_name, v_anchor_name = self.anchor_ids
            _u = AnchorPoint(self.u).anchor_points[u_anchor_name]
            _v = AnchorPoint(self.v).anchor_points[v_anchor_name]
            if self.autopath:
                self._path = self.u._ctx.canvas.shortest_path(_u, _v)
            else:
                line = LineString([_u, _v])
                self._path = redistribute_vertices(line, line.length / 3)
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def anchor_ids(self):
        """Return studio anchor ids."""
        if isinstance(self.loc, tuple):
            loc_u, loc_v = self.loc
        else:
            loc_u = self.loc
            loc_v = self.loc
        return AnchorPoint(self.u).studio_anchor(self.v, (loc_u, loc_v))

    def __repr__(self):
        """Return Deck representation of self."""
        return self._to_deck()

    def set_color(self, color):
        """Set the color of the line."""
        self._color = color

    def get_color(self):
        """Return the line color."""
        return self._color

    def set_linestyle(self, ls):
        """Set the linestyle of the line.

        Args:
            ls (str): Possible values: '-' or 'solid', '--' or 'dashed', '-.' or
                'dashdot', ':' or 'dotted', '-.' or 'dashdotdot'.
        """
        if isinstance(ls, str):
            self._linestyle = ls

    def get_linestyle(self):
        """Return the linestyle.

        See also :meth:`~trnsystor.trnsysmodel.LinkStyle.set_linestyle`.
        """
        return self._linestyle

    def set_linewidth(self, lw):
        """Set the line width in points.

        Args:
            lw (float): The line width in points.
        """
        self._linewidth = lw

    def get_linewidth(self):
        """Return the linewidth.

        See also :meth:`~trnsystor.trnsysmodel.LinkStyle.set_linewidth`.
        """
        return self._linewidth

    def _to_deck(self):
        """Return deck representation of self.

        Examples:
            0:20:40:20:1:0:0:0:1:513,441:471,441:471,430:447,430
        """
        u_anchor_name, v_anchor_name = self.anchor_ids
        anchors = (
            ":".join(
                [
                    ":".join(
                        map(
                            str,
                            AnchorPoint(self.u).studio_anchor_mapping[u_anchor_name],
                        )
                    ),
                    ":".join(
                        map(
                            str,
                            AnchorPoint(self.u).studio_anchor_mapping[v_anchor_name],
                        )
                    ),
                ]
            )
            + ":"
        )

        rgb = _to_rgb(self.get_color())
        color = (
            str(get_int_from_rgb(tuple(c * 255 for c in rgb)))
            + ":"
        )
        raw_path = self.path
        if raw_path is None:
            coords = []
        elif hasattr(raw_path, "coords"):
            coords = [tuple(int(v) for v in pt) for pt in raw_path.coords]
        else:
            coords = [tuple(int(v) for v in pt) for pt in raw_path]
        # Handle single-point case (flatten 1-d)
        if coords and not isinstance(coords[0], tuple | list):
            coords = [tuple(coords)]
        path = ",".join([":".join(map(str, pt)) for pt in coords])
        linestyle = str(_linestyle_to_studio(self.get_linestyle())) + ":"
        linewidth = str(self.get_linewidth()) + ":"
        connection_set = anchors + "1:" + color + linestyle + linewidth + "1:" + path
        head = f"*!LINK {self.u.unit_number}:{self.v.unit_number}\n"
        tail = f"*!CONNECTION_SET {connection_set}\n"
        return head + tail


def _linestyle_to_studio(ls):
    linestyle_dict = {
        "-": 0,
        "solid": 0,
        "--": 1,
        "dashed": 1,
        ":": 2,
        "dotted": 2,
        "-.": 3,
        "dashdot": 3,
        "-..": 4,
        "dashdotdot": 4,
    }
    _ls = linestyle_dict.get(ls)
    return _ls


def _studio_to_linestyle(ls):
    linestyle_dict = {0: "-", 1: "--", 2: ":", 3: "-.", 4: "-.."}
    _ls = linestyle_dict.get(ls)
    return _ls
