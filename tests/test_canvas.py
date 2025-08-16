from shapely.geometry import Point

from trnsystor.canvas import StudioCanvas


def test_shortest_path_uses_step():
    canvas = StudioCanvas(width=20, height=10, step=10)
    start = Point(0, 0)
    end = Point(20, 0)
    path = canvas.shortest_path(start, end, donotcross=False)
    assert path is not None
    assert list(path.coords) == [(0, 0), (10, 0), (20, 0)]


def test_blocked_edges_prevent_reuse():
    canvas = StudioCanvas(width=20, height=10, step=10)
    start = Point(0, 0)
    end = Point(20, 0)
    first = canvas.shortest_path(start, end, donotcross=True)
    assert first is not None
    second = canvas.shortest_path(start, end, donotcross=True)
    assert list(second.coords) == [
        (0, 0),
        (0, 10),
        (10, 10),
        (20, 10),
        (20, 0),
    ]
