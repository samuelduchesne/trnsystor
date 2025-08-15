"""Test anchorpoint module."""

from types import SimpleNamespace
from shapely.geometry import Point

from trnsystor.anchorpoint import AnchorPoint


class DummyModel:
    """Minimal model with studio position for AnchorPoint tests."""

    def __init__(self, x=0, y=0):
        self.studio = SimpleNamespace(position=Point(x, y))


def test_anchor_points_are_unique():
    """All eight anchor points should be unique."""
    model = DummyModel()
    ap = AnchorPoint(model, offset=10)
    coords = [(pt.x, pt.y) for pt in ap.anchor_points.values()]
    assert len(coords) == 8
    assert len(set(coords)) == 8
