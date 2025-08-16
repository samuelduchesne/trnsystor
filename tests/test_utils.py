"""Test utils module."""
import pytest

from trnsystor.utils import affine_transform, parse_unit, redistribute_vertices, ureg


class TestRedistributeVertices:
    @pytest.fixture
    def line(self):
        from shapely.geometry.polygon import LineString

        line = LineString([(0, 0), (1, 1), (2, 2)])
        yield line

    @pytest.fixture
    def ring(self):
        from shapely.geometry.polygon import LinearRing

        ring = LinearRing([(0, 0), (1, 1), (1, 0)])
        yield ring

    @pytest.fixture
    def zero_geom(self):
        from shapely.geometry.polygon import LineString

        line = LineString([(1, 1), (1, 1)])
        yield line

    def test_redistribute_vertices(self, line):
        newline = redistribute_vertices(line, 10)
        assert newline.length == line.length

    def test_redistribute_vertices_wrongtype(self, ring):
        """Tests unsupported geometry."""
        with pytest.raises(TypeError):
            assert redistribute_vertices(ring, 10)

    def test_redistribute_vertices_zero(self, zero_geom):
        new_goem = redistribute_vertices(zero_geom, 10)
        assert new_goem.length == 0
        assert new_goem == zero_geom


def test_parse_unit_percent_multiple_calls():
    """``parse_unit`` can be called repeatedly for percent."""
    for _ in range(3):
        Q_, unit = parse_unit("% (base 100)")
        assert unit == ureg.percent


def test_parse_unit_fraction_multiple_calls():
    """``parse_unit`` can be called repeatedly for fraction."""
    for _ in range(3):
        Q_, unit = parse_unit("fraction")
        assert unit == ureg.fraction


def test_parse_unit_custom_unit_repeated_calls():
    """Custom units defined at runtime are parsed correctly multiple times."""
    if "widget" not in ureg:
        ureg.define("widget = 3 * meter")
    for _ in range(3):
        Q_, unit = parse_unit("widget")
        assert unit == ureg.widget


def test_affine_transform_default_flip():
    """Without a matrix, geometry should be mirrored across the x-axis."""
    from shapely.geometry import Point

    geom = Point(2, 3)
    new_geom = affine_transform(geom, matrix=None)
    assert new_geom.x == pytest.approx(2)
    assert new_geom.y == pytest.approx(-3)


def test_affine_transform_with_matrix_translation():
    """Affine transform should apply provided matrix."""
    import numpy as np
    from shapely.geometry import Point

    class MatrixWrapper:
        def __init__(self, data):
            self.array = np.array(data)

        def __getitem__(self, idx):
            return self.array[idx]

        def __bool__(self):
            return True

    geom = Point(1, 2)
    matrix = MatrixWrapper([[1, 0, 5], [0, 1, 3], [0, 0, 1]])
    new_geom = affine_transform(geom, matrix=matrix)
    assert new_geom.x == pytest.approx(6)
    assert new_geom.y == pytest.approx(5)
