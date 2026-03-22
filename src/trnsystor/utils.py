"""Utils module."""

import functools
import math
import re

from shapely.affinity import affine_transform as _affine_transform
from shapely.geometry import LineString

from trnsystor.quantity import Quantity

# Pre-compiled regexes
_STANDARDIZE_RE = re.compile("[^0-9a-zA-Z]+")


def find_closest(mappinglist, coordinate):
    """Find the closest point in *mappinglist* to *coordinate*."""
    from shapely.geometry import Point

    return min(
        mappinglist,
        key=lambda x: Point(x).distance(Point(coordinate)),
    )


def affine_transform(geom, matrix=None):
    """Apply affine transformation to geometry.

    By, default, flip geometry along the x axis.

    Hint:
        visit affine_matrix_ for other affine transformation matrices.

    .. _affine_matrix: https://en.wikipedia.org/wiki/Affine_transformation#/media/File:2D_affine_transformation_matrix.svg

    Args:
        geom (BaseGeometry): The geometry.
        matrix (list): The 3x3 coefficient matrix as a list of lists.
    """
    if not matrix:
        # Default: flip geometry along the x axis
        # [a, b, d, e, xoff, yoff] for shapely affine_transform
        matrix_l = [1, 0, 0, -1, 0, 0]
    else:
        matrix_l = [
            matrix[0][0],
            matrix[0][1],
            matrix[1][0],
            matrix[1][1],
            matrix[0][2],
            matrix[1][2],
        ]
    return _affine_transform(geom, matrix_l)


def get_rgb_from_int(rgb_int):
    """Convert an rgb int color to its red, green and blue colors.

    Values are used ranging from 0 to 255 for each of the components.

    Important:
        Unlike Java, the TRNSYS Studio will want an integer where bits 0-7 are
        the blue value, 8-15 the green, and 16-23 the red.

    Examples:
        Get the rgb tuple from a an rgb int.

        >>> get_rgb_from_int(9534163)
        (211, 122, 145)

    Args:
        rgb_int (int): An rgb int representation.

    Returns:
        (tuple): (r, g, b) tuple.
    """
    red = rgb_int & 255
    green = (rgb_int >> 8) & 255
    blue = (rgb_int >> 16) & 255
    return red, green, blue


def get_int_from_rgb(rgb):
    """Convert an RBG color to its TRNSYS Studio compatible int color.

    Values are used ranging from 0 to 255 for each of the components.

    Important:
        Unlike Java, the TRNSYS Studio will want an integer where bits 0-7 are
        the blue value, 8-15 the green, and 16-23 the red.

    Examples:
        Get the rgb int from an rgb 3-tuple

        >>> get_int_from_rgb((211, 122, 145))
        9534163

    Args:
        rgb (tuple): The red, green and blue values. All values assumed to be in
            range [0, 255].

    Returns:
        (int): the rgb int.
    """
    red, green, blue = map(int, rgb)
    rgb_int = (blue << 16) + (green << 8) + red
    return rgb_int


def resolve_type(args):
    """Return float for :class:`Quantity` or number."""
    if isinstance(args, Quantity):
        return args.m
    else:
        return float(args)


def _parse_value(value, _type, unit, bounds=(-math.inf, math.inf), name=None):
    if not name:
        name = ""
    _type = parse_type(_type)
    unit_ = parse_unit(unit)

    try:
        f = _type(value)
    except ValueError:
        # invalid literal for int() with base 10: '+Inf'
        if value in {"STEP", "START"}:
            value = 1
        elif value == "STOP":
            value = 8760
        f = float(value)
    if isinstance(f, str):
        return f
    xmin, xmax = map(resolve_type, bounds)
    is_bound = xmin <= f <= xmax
    if is_bound:
        if unit_:
            return Quantity(f, unit_)
    else:
        # out of bounds
        msg = (
            f'Value {name} "{f}" is out of bounds. '
            f"{Quantity(xmin, unit_)} <= value <= {Quantity(xmax, unit_)}"
        )
        raise ValueError(msg)


def parse_type(_type):
    """Parse type str as builtin type."""
    if isinstance(_type, type):
        return _type
    elif _type == "integer":
        return int
    elif _type == "real":
        return float
    elif _type == "string":
        return str
    else:
        raise NotImplementedError()


def standardize_name(name):
    """Replace invalid characters with underscores."""
    return _STANDARDIZE_RE.sub("_", name)


# ---------------------------------------------------------------------------
# Unit mapping: TRNSYS proforma unit strings → canonical unit names
# ---------------------------------------------------------------------------
_UNIT_MAP: dict[str, str] = {
    "% (base 100)": "percent",
    "c": "degC",
    "deltac": "delta_degC",
    "fraction": "fraction",
    "any": "dimensionless",
}


@functools.lru_cache(maxsize=64)
def parse_unit(unit: str | None) -> str:
    """Return the canonical unit string for a TRNSYS proforma unit.

    Args:
        unit: A string unit from a proforma XML.

    Returns:
        The canonical unit string (e.g. ``"degC"``, ``"kg/hr"``).
    """
    if unit in {"-", None}:
        return "dimensionless"
    unit_l = unit.lower()
    mapped = _UNIT_MAP.get(unit_l)
    if mapped is not None:
        return mapped
    # Pass through standard units as-is (e.g. "kg/hr", "m^2", "kJ/hr.m.K")
    return unit


def redistribute_vertices(geom, distance):
    """Redistribute vertices by a certain distance.

    Hint:
        https://stackoverflow.com/a/35025274

    Args:
        geom (LineString): The geometry.
        distance (float): The distance used to redistribute vertices.
    """
    if geom.length == 0:
        return geom
    if geom.geom_type == "LineString":
        num_vert = round(geom.length / distance)
        if num_vert == 0:
            num_vert = 1
        return LineString(
            [
                geom.interpolate(float(n) / num_vert, normalized=True)
                for n in range(num_vert + 1)
            ]
        )
    else:
        raise TypeError("unhandled geometry %s", (geom.geom_type,))


# ---------------------------------------------------------------------------
# Sympy-dependent utilities (lazy-loaded)
# ---------------------------------------------------------------------------


def _get_deck_file_printer_class():
    """Return the DeckFilePrinter class, importing sympy on first call."""
    from sympy.printing import StrPrinter

    class DeckFilePrinter(StrPrinter):
        """Print derivative of a function of symbols in deck file form."""

        def _print_Symbol(self, expr):
            """Print the TypeVariable's unit_number and output number."""
            try:
                return f"[{expr.model.model.unit_number}, {expr.model.one_based_idx}]"
            except AttributeError:
                return expr.name

    return DeckFilePrinter


def _get_type_variable_symbol_class():
    """Return the TypeVariableSymbol class, importing sympy on first call."""
    from sympy import Expr, Symbol, cacheit

    class TypeVariableSymbol(Symbol):
        """Subclass of sympy Symbol for TypeVariable references."""

        def __new__(cls, type_variable, **assumptions):
            """:class:`TypeVariableSymbol` are identified by TypeVariable and
            assumptions

            Args:
                type_variable (TypeVariable): The TypeVariable to defined as a
                    Symbol.
                **assumptions: See :mod:`sympy.core.assumptions` for more details.
            """
            cls._sanitize(assumptions, cls)
            return TypeVariableSymbol.__xnew_cached_(cls, type_variable, **assumptions)

        def __new_stage2__(cls, model, **assumptions):  # type: ignore[override]
            """Return new stage."""
            obj = Expr.__new__(cls)  # type: ignore[arg-type]
            obj.name = model.name
            obj.model = model

            tmp_asm_copy = assumptions.copy()

            assumptions_kb, assumptions_orig, assumptions0 = (
                Symbol._canonical_assumptions(**assumptions)
            )
            obj._assumptions = assumptions_kb
            obj._assumptions._generator = tmp_asm_copy  # Issue #8873
            obj._assumptions_orig = assumptions_orig
            obj._assumptions0 = tuple(sorted(assumptions0.items()))
            return obj

        __xnew__ = staticmethod(__new_stage2__)  # type: ignore[assignment]
        __xnew_cached_ = staticmethod(cacheit(__new_stage2__))  # type: ignore[assignment]

    return TypeVariableSymbol


# Lazy singletons — instantiated on first access
_DeckFilePrinter = None
_TypeVariableSymbol = None


def _ensure_sympy():
    """Ensure sympy classes are loaded, raising a clear error if missing."""
    global _DeckFilePrinter, _TypeVariableSymbol
    if _DeckFilePrinter is None:
        try:
            _DeckFilePrinter = _get_deck_file_printer_class()
            _TypeVariableSymbol = _get_type_variable_symbol_class()
        except ImportError as e:
            raise ImportError(
                "sympy is required for symbolic equation support. "
                "Install it with: pip install trnsystor[symbolic]"
            ) from e


class _LazyDeckFilePrinter:
    """Proxy that lazily loads the real DeckFilePrinter."""

    def __call__(self):
        _ensure_sympy()
        return _DeckFilePrinter()


class _LazyTypeVariableSymbol:
    """Proxy that lazily loads the real TypeVariableSymbol."""

    def __call__(self, *args, **kwargs):
        _ensure_sympy()
        return _TypeVariableSymbol(*args, **kwargs)


# Public names that match the old API
DeckFilePrinter = _LazyDeckFilePrinter()
TypeVariableSymbol = _LazyTypeVariableSymbol()


def print_my_latex(expr):
    """Print expression in deck file format using DeckFilePrinter."""
    printer = DeckFilePrinter()
    return printer.doprint(expr)
