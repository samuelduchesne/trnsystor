import pytest
from shapely.geometry import Point

from trnsystor.canvas import StudioCanvas


def test_step_size_coordinates():
    canvas = StudioCanvas(width=10, height=10, step=2)
    path = canvas.shortest_path(Point(0, 0), Point(10, 10))
    assert list(path.coords)[0] == (0.0, 0.0)
    assert list(path.coords)[-1] == (10.0, 10.0)
    for x, y in path.coords:
        assert x % 2 == 0 and y % 2 == 0


def test_blocking_edges():
    canvas = StudioCanvas(width=10, height=10, step=1)
    start = Point(0, 0)
    end = Point(4, 0)
    first = canvas.shortest_path(start, end)
    second = canvas.shortest_path(start, end)
    assert first.length < second.length
