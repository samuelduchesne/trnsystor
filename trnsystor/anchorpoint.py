# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import itertools

from shapely.geometry import MultiPoint


class AnchorPoint(object):
    """Handles the anchor point. There are 6 anchor points around a component"""

    def __init__(self, model, offset=20, height=40, width=40):
        """
        Args:
            model (Component): The Component.
            offset (float): The offset to give the anchor points from the center
                of the model position.
            height (float): The height of the component in points.
            width (float): The width of the component in points.
        """
        self.offset = offset
        self.model = model
        self.height = height
        self.width = width

    def studio_anchor(self, other, loc):
        """Return the studio anchor based on a location.

        Args:
            other: TrnsysModel
            loc (2-tuple):
        """
        if "best" not in loc:
            return loc
        u_loc, v_loc = loc
        if u_loc == "best":
            u_loc, _ = self.find_best_anchors(other)
        if v_loc == "best":
            _, v_loc = self.find_best_anchors(other)
        return u_loc, v_loc

    def find_best_anchors(self, other):
        """
        Args:
            other:
        """
        dist = {}
        for u in self.anchor_points.values():
            for v in other.anchor_points.values():
                dist[((u.x, u.y), (v.x, v.y))] = u.distance(v)
        (u_coords, v_coords), distance = sorted(dist.items(), key=lambda kv: kv[1])[0]
        u_loc, v_loc = (
            self.reverse_anchor_points[u_coords],
            AnchorPoint(other).reverse_anchor_points[v_coords],
        )
        return u_loc, v_loc

    @property
    def anchor_points(self):
        return self.get_octo_pts_dict(self.offset)

    @property
    def reverse_anchor_points(self):
        pts = self.get_octo_pts_dict(self.offset)
        return {(pt.x, pt.y): key for key, pt in pts.items()}

    @property
    def studio_anchor_mapping(self):
        from shapely.affinity import translate

        p_ = {}
        minx, miny, maxx, maxy = MultiPoint(
            [p for p in self.anchor_points.values()]
        ).bounds
        for k, p in self.anchor_points.items():
            p_[k] = translate(p, -minx, -maxy)
        minx, miny, maxx, maxy = MultiPoint([p for p in p_.values()]).bounds
        for k, p in p_.items():
            p_[k] = translate(p, 0, -miny)
        return {
            k: tuple(itertools.chain(*tuple((map(abs, p) for p in p.coords))))
            for k, p in p_.items()
        }

    @property
    def studio_anchor_reverse_mapping(self):
        return {
            (0, 0): "top-left",
            (20, 0): "top-center",
            (40, 0): "top-right",
            (40, 20): "center-right",
            (40, 40): "bottom-right",
            (20, 40): "bottom-center",
            (0, 40): "bottom-left",
            (0, 20): "center-left",
        }

    def get_octo_pts_dict(self, offset=10):
        """Define 8-anchor :class:`Point` around the :class:`TrnsysModel` in
        cartesian space and return a named-dict with human readable meaning.
        These points are equally dispersed at the four corners and 4 edges of
        the center, at distance = :attr:`offset`

        See :func:`~trnsysmodel.TrnsysType.set_link_style` or
        :class:`trnsysmodel.LinkStyle` for more details.

        Args:
            offset (float): The offset around the center point of :attr:`self`.

        Note:
            In the Studio, a component has 8 anchor points at the four corners
            and four edges. units.Links can be created on these connections.

            .. image:: ../_static/anchor-pts.png
        """
        from shapely.affinity import translate

        center = self.centroid
        xy_offset = {
            "top-left": (-offset, offset),
            "top-center": (0, offset),
            "top-right": (offset, offset),
            "center-right": (offset, 0),
            "bottom-right": (-offset, -offset),
            "bottom-center": (0, -offset),
            "bottom-left": (-offset, -offset),
            "center-left": (-offset, 0),
        }
        return {key: translate(center, *offset) for key, offset in xy_offset.items()}

    @property
    def centroid(self):
        return self.model.studio.position
