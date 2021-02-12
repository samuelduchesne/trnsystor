"""Utils module."""
import math
import re

from pint import UnitRegistry
from pint.quantity import _Quantity
from shapely.geometry import LineString
from sympy import Expr, Symbol, cacheit
from sympy.core.assumptions import StdFactKB
from sympy.core.logic import fuzzy_bool
from sympy.printing import StrPrinter


def affine_transform(geom, matrix=None):
    """Apply affine transformation to geometry.

    By, default, flip geometry along the x axis.

    Hint:
        visit affine_matrix_ for other affine transformation matrices.

    .. _affine_matrix: https://en.wikipedia.org/wiki/Affine_transformation#/media/File:2D_affine_transformation_matrix.svg

    Args:
        geom (BaseGeometry): The geometry.
        matrix (np.array): The coefficient matrix is provided as a list or
            tuple.
    """
    import numpy as np
    from shapely.affinity import affine_transform

    if not matrix:
        matrix = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]])
    matrix_l = matrix[0:2, 0:2].flatten().tolist() + matrix[0:2, 2].flatten().tolist()
    return affine_transform(geom, matrix_l)


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
    """Return float for :class:`_Quantity` or number."""
    if isinstance(args, _Quantity):
        return args.m
    else:
        return float(args)


def _parse_value(value, _type, unit, bounds=(-math.inf, math.inf), name=None):
    if not name:
        name = ""
    _type = parse_type(_type)
    Q_, unit_ = parse_unit(unit)

    try:
        f = _type(value)
    except ValueError:
        # invalid literal for int() with base 10: '+Inf'
        if value == "STEP":
            value = 1
            # Todo: figure out better logic when default value is 'STEP'
        elif value == "START":
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
            return Q_(f, unit_)
    else:
        # out of bounds
        msg = 'Value {} "{}" is out of bounds. ' "{xmin} <= value <= {xmax}".format(
            name, f, xmin=Q_(xmin, unit_), xmax=Q_(xmax, unit_)
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
    return re.sub("[^0-9a-zA-Z]+", "_", name)


def parse_unit(unit):
    """Return supported unit.

    Units defined in the xml proformas follow a convention that is not quite
    compatible with `Pint` . This method will catch known discrepancies.

    Args:
        unit (str): A string unit.

    Returns:
        2-tuple: The Quantity class and the Unit class
            * ureg.Quantity: The Quantity class
            * ureg.Unit: The Unit class
    """
    Q_ = ureg.Quantity
    if unit == "-" or unit is None:
        return Q_, ureg.parse_expression("dimensionless")
    elif unit == "% (base 100)":
        ureg.define("percent = 0.01*count = %")
        return Q_, ureg.percent
    elif unit.lower() == "c":
        Q_ = ureg.Quantity
        return Q_, ureg.degC
    elif unit.lower() == "deltac":
        Q_ = ureg.Quantity
        return Q_, ureg.delta_degC
    elif unit.lower() == "fraction":
        ureg.define("fraction = 1*count = -")
        return Q_, ureg.fraction
    elif unit.lower() == "any":
        return Q_, ureg.parse_expression("dimensionless")
    else:
        return Q_, ureg.parse_units(unit)


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
        num_vert = int(round(geom.length / distance))
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


ureg = UnitRegistry()


class DeckFilePrinter(StrPrinter):
    """Print derivative of a function of symbols in deck file form.

    This will override the :func:`sympy.printing.str.StrPrinter#_print_Symbol` method to
    print the TypeVariable's unit_number and output number.
    """

    def _print_Symbol(self, expr):
        """Print the TypeVariable's unit_number and output number."""
        try:
            return "[{}, {}]".format(
                expr.model.model.unit_number, expr.model.one_based_idx
            )
        except AttributeError:
            # 'Symbol' object has no attribute 'model'
            return expr.name


def print_my_latex(expr):
    """Most of the printers define their own wrappers for print().

    These wrappers usually take printer settings. Our printer does not have any
    settings.
    """
    return DeckFilePrinter().doprint(expr)


class TypeVariableSymbol(Symbol):
    """This is a subclass of the sympy Symbol class.

    It is a bit of a hack, so hopefully nothing bad will happen.
    """

    def __new__(cls, type_variable, **assumptions):
        """:class:`TypeVariableSymbol` are identified by TypeVariable and assumptions.

        >>> from trnsystor.utils import TypeVariableSymbol
        >>> TypeVariableSymbol("x") == TypeVariableSymbol("x")
        True
        >>> TypeVariableSymbol("x", real=True) == TypeVariableSymbol("x",
        real=False)
        False

        Args:
            type_variable (TypeVariable): The TypeVariable to defined as a
                Symbol.
            **assumptions: See :mod:`sympy.core.assumptions` for more details.
        """
        cls._sanitize(assumptions, cls)
        return TypeVariableSymbol.__xnew_cached_(cls, type_variable, **assumptions)

    def __new_stage2__(cls, model, **assumptions):
        """Return new stage."""
        obj = Expr.__new__(cls)
        obj.name = model.name
        obj.model = model

        tmp_asm_copy = assumptions.copy()

        # be strict about commutativity
        is_commutative = fuzzy_bool(assumptions.get("commutative", True))
        assumptions["commutative"] = is_commutative
        obj._assumptions = StdFactKB(assumptions)
        obj._assumptions._generator = tmp_asm_copy  # Issue #8873
        return obj

    __xnew__ = staticmethod(__new_stage2__)  # never cached (e.g. dummy)
    __xnew_cached_ = staticmethod(cacheit(__new_stage2__))  # symbols are always cached
