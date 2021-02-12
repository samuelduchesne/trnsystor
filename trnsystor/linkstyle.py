"""LinkStyle module."""
import numpy as np
from matplotlib.colors import colorConverter
from shapely.geometry import LineString

from trnsystor.anchorpoint import AnchorPoint
from trnsystor.utils import get_int_from_rgb, redistribute_vertices


class LinkStyle(object):
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
            color (str or tuple): The color of the line. Accepts any matplotlib
                color. You can specify colors in many ways, including full names
                ('green'), hex strings ('#008000'), RGB or RGBA tuples
                ((0,1,0,1)) or grayscale intensities as a string ('0.8').
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
                self._path = self.u.STUDIO_CANVAS.shortest_path(_u, _v)
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

        color = (
            str(
                get_int_from_rgb(
                    tuple([u * 255 for u in colorConverter.to_rgb(self.get_color())])
                )
            )
            + ":"
        )
        path = ",".join(
            [":".join(map(str, n.astype(int).tolist())) for n in np.array(self.path)]
        )
        linestyle = str(_linestyle_to_studio(self.get_linestyle())) + ":"
        linewidth = str(self.get_linewidth()) + ":"
        connection_set = anchors + "1:" + color + linestyle + linewidth + "1:" + path
        head = "*!LINK {}:{}\n".format(self.u.unit_number, self.v.unit_number)
        tail = "*!CONNECTION_SET {}\n".format(connection_set)
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
