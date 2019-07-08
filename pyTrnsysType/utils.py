import math
import re

from pint import UnitRegistry
from pint.quantity import _Quantity
from shapely.geometry import LineString
from sympy import Symbol, Expr, cacheit
from sympy.core.assumptions import StdFactKB
from sympy.core.logic import fuzzy_bool


def affine_transform(geom, matrix=None):
    """Apply affine transformation to geometry. By, default, flip geometry along
    the x axis.

    Hint:
        visit affine_matrix_ for other affine transformation matrices.

    .. _affine_matrix: https://en.wikipedia.org/wiki/Affine_transformation

    #/media/ File:2D_affine_transformation_matrix.svg

    Args:
        geom (BaseGeometry): The geometry.
        matrix (np.array): The coefficient matrix is provided as a list or
            tuple.
    """
    import numpy as np
    from shapely.affinity import affine_transform
    if not matrix:
        matrix = np.array([[1, 0, 0],
                           [0, -1, 0],
                           [0, 0, 0]])
    matrix_l = matrix[0:2, 0:2].flatten().tolist() + \
               matrix[0:2, 2].flatten().tolist()
    return affine_transform(geom, matrix_l)


def get_rgb_from_int(rgb_int):
    """
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
    """
    Examples:
        Get the rgb int from an rgb 3-tuple >>> get_int_from_rgb((211, 122,
        145)) 9534163

    Args:
        rgb (tuple): (r, g, b)

    Returns:
        (int): the rgb int.
    """
    red, green, blue = map(int, rgb)
    rgb_int = (blue << 16) + (green << 8) + red
    return rgb_int


def resolve_type(args):
    """
    Args:
        args:
    """
    if isinstance(args, _Quantity):
        return args.m
    else:
        return float(args)


def _parse_value(value, _type, unit, bounds=(-math.inf, math.inf), name=None):
    """
    Args:
        value:
        _type:
        unit:
        bounds:
        name:
    """
    if not name:
        name = ''
    _type = parse_type(_type)
    Q_, unit_ = parse_unit(unit)

    try:
        f = _type(value)
    except:
        f = float(value)
    xmin, xmax = map(resolve_type, bounds)
    is_bound = xmin <= f <= xmax
    if is_bound:
        if unit_:
            return Q_(f, unit_)
    else:
        # out of bounds
        msg = 'Value {} "{}" is out of bounds. ' \
              '{xmin} <= value <= {xmax}'.format(name, f, xmin=Q_(xmin, unit_),
                                                 xmax=Q_(xmax, unit_))
        raise ValueError(msg)


def parse_type(_type):
    """
    Args:
        _type (type or str):
    """
    if isinstance(_type, type):
        return _type
    elif _type == 'integer':
        return int
    elif _type == 'real':
        return float
    else:
        raise NotImplementedError()


def standerdized_name(name):
    """
    Args:
        name:
    """
    return re.sub('[^0-9a-zA-Z]+', '_', name)


def parse_unit(unit):
    """Units defined in the xml proformas follow a convention that is not quite
    compatible with `Pint` . This method will catch known discrepancies.

    Args:
        unit (str): A string unit.

    Returns:
        2-tuple: The Quantity class and the Unit class
            * ureg.Quantity: The Quantity class
            * ureg.Unit: The Unit class
    """
    Q_ = ureg.Quantity
    if unit == '-' or unit is None:
        return Q_, ureg.parse_expression('dimensionless')
    elif unit == '% (base 100)':
        ureg.define('percent = 0.01*count = %')
        return Q_, ureg.percent
    elif unit.lower() == 'c':
        Q_ = ureg.Quantity
        return Q_, ureg.degC
    elif unit.lower() == 'deltac':
        Q_ = ureg.Quantity
        return Q_, ureg.delta_degC
    elif unit.lower() == 'fraction':
        ureg.define('fraction = 1*count = -')
        return Q_, ureg.fraction
    else:
        return Q_, ureg.parse_units(unit)


def redistribute_vertices(geom, distance):
    """from https://stackoverflow.com/a/35025274

    Args:
        geom:
        distance:
    """
    if geom.geom_type == 'LineString':
        num_vert = int(round(geom.length / distance))
        if num_vert == 0:
            num_vert = 1
        return LineString(
            [geom.interpolate(float(n) / num_vert, normalized=True)
             for n in range(num_vert + 1)])
    else:
        raise ValueError('unhandled geometry %s', (geom.geom_type,))


ureg = UnitRegistry()

from sympy.printing import StrPrinter


class MyLatexPrinter(StrPrinter):
    """Print derivative of a function of symbols in a shorter form.
    """

    def _print_Symbol(self, expr):
        return "[{}, {}]".format(
            expr.model.model.unit_number,
            expr.model.one_based_idx)


def print_my_latex(expr):
    """ Most of the printers define their own wrappers for print().
    These wrappers usually take printer settings. Our printer does not have
    any settings.
    """
    return MyLatexPrinter().doprint(expr)


def pre(expr):
    print(expr)
    for arg in expr.args:
        pre(arg)


class TypeVariableSymbol(Symbol):
    def __new__(cls, name, **assumptions):
        """Symbols are identified by name and assumptions::

        >>> from sympy import Symbol
        >>> Symbol("x") == Symbol("x")
        True
        >>> Symbol("x", real=True) == Symbol("x", real=False)
        False

        """
        cls._sanitize(assumptions, cls)
        return TypeVariableSymbol.__xnew_cached_(cls, name, **assumptions)

    def __new_stage2__(cls, model, **assumptions):
        obj = Expr.__new__(cls)
        obj.name = model.name
        obj.model = model

        # TODO: Issue #8873: Forcing the commutative assumption here means
        # later code such as ``srepr()`` cannot tell whether the user
        # specified ``commutative=True`` or omitted it.  To workaround this,
        # we keep a copy of the assumptions dict, then create the StdFactKB,
        # and finally overwrite its ``._generator`` with the dict copy.  This
        # is a bit of a hack because we assume StdFactKB merely copies the
        # given dict as ``._generator``, but future modification might, e.g.,
        # compute a minimal equivalent assumption set.
        tmp_asm_copy = assumptions.copy()

        # be strict about commutativity
        is_commutative = fuzzy_bool(assumptions.get('commutative', True))
        assumptions['commutative'] = is_commutative
        obj._assumptions = StdFactKB(assumptions)
        obj._assumptions._generator = tmp_asm_copy  # Issue #8873
        return obj

    __xnew__ = staticmethod(
        __new_stage2__)  # never cached (e.g. dummy)
    __xnew_cached_ = staticmethod(
        cacheit(__new_stage2__))  # symbols are always cached
