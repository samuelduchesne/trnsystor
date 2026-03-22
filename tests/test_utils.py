"""Test utils module."""

import pytest

from trnsystor.quantity import Quantity
from trnsystor.utils import parse_unit, redistribute_vertices


class TestRedistributeVertices:
    @pytest.fixture
    def line(self):
        from shapely.geometry.polygon import LineString

        line = LineString([(0, 0), (1, 1), (2, 2)])
        return line

    @pytest.fixture
    def ring(self):
        from shapely.geometry.polygon import LinearRing

        ring = LinearRing([(0, 0), (1, 1), (1, 0)])
        return ring

    @pytest.fixture
    def zero_geom(self):
        from shapely.geometry.polygon import LineString

        line = LineString([(1, 1), (1, 1)])
        return line

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
        unit = parse_unit("% (base 100)")
        assert unit == "percent"


def test_parse_unit_fraction_multiple_calls():
    """``parse_unit`` can be called repeatedly for fraction."""
    for _ in range(3):
        unit = parse_unit("fraction")
        assert unit == "fraction"


def test_quantity_basic():
    """Test basic Quantity operations."""
    q = Quantity(10.0, "degC")
    assert q.m == 10.0
    assert q.units == "degC"
    assert float(q) == 10.0
    assert int(q) == 10


def test_quantity_to():
    """Test Quantity unit conversion."""
    q = Quantity(1.0, "l/s")
    converted = q.to("m^3/s")
    assert abs(converted.m - 0.001) < 1e-12
    assert converted.units == "m^3/s"


def test_quantity_format():
    """Test Quantity ~P format."""
    q = Quantity(20.0, "degC")
    formatted = f"{q:~P}"
    assert "20" in formatted
    assert "°C" in formatted
