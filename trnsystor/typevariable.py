"""TypeVariable module."""
import collections
import copy
import re

from bs4 import Tag

from trnsystor.linkstyle import LinkStyle
from trnsystor.utils import _parse_value, parse_type, standardize_name


class TypeVariable(object):
    """TypeVariable class.

    :class:`TypeVariable` is the main object class that handles storage of
    TRNSYS component parameters, inputs, outputs and derivatives. Parameters,
    Inputs, Outputs and Derivatives are all subclasses of TypeVariable.

    * See :class:`Parameter` for more details.
    * See :class:`Input` for more details.
    * See :class:`Output` for more details.
    * See :class:`Derivative` for more details.
    """

    def __init__(
        self,
        val,
        order=None,
        name=None,
        role=None,
        dimension=None,
        unit=None,
        type=None,
        min=None,
        max=None,
        boundaries=None,
        default=None,
        symbol=None,
        definition=None,
        model=None,
    ):
        """Initialize a TypeVariable with the following attributes.

        Args:
            val (int, float, _Quantity): The actual value hold by this object.
            order (str): The order of the variable.
            name (str): This name will be seen by the user in the connections
                window and all other variable information windows.
            role (str): The role of the variables such as input, output, etc.
                Changing the role of a standard component requires reprogramming
                and recompiling the component.
            dimension (str): The dimension of the variable (power, temperature,
                etc.): This dimension must be already defined in the unit
                dictionary (refer to section 2.9) to be used. The pre-defined
                dimension ‘any’ allows to make a variable compatible with any
                other variable: no checks are performed on such variables if the
                user attempts to connect them to other variables.
            unit (str): The unit of the variable that the TRNSYS program
                requires for the specified dimension (C, F, K etc.)
            type (type or str): The type of the variable: Real, integer,
                Boolean, or string.
            min (int, float or pint._Quantity): The minimum value. The minimum
                and maximum can be "-INF" or "+INF" to indicate no limit
                (infinity). +/-INF is the default value.
            max (int, float or pint._Quantity): The maximum value. The minimum
                and maximum can be "-INF" or "+INF" to indicate no limit
                (infinity). +/-INF is the default value.
            boundaries (str): This setting determines if the minimum and maximum
                are included or not in the range. choices are "[;]", "[;[",
                "];]" ,"];["
            default (int, float or pint._Quantity): the default value of the
                variable. The default value is replaced by the initial value for
                the inputs and derivatives and suppressed for the outputs.
            symbol (str): The symbol of the unit (not used).
            definition (str): A short description of the variable.
            model (TrnsysModel): the TrnsysModel this TypeVariable belongs to.
        """
        super().__init__()
        self._is_question = False
        self._iscycle = False
        self._iscyclebase = False
        self.order = order
        self.name = name
        self.role = role
        self.dimension = dimension
        self.unit = (
            unit
            if unit is None
            else re.sub(r"([\s\S\.]*)\/([\s\S\.]*)", r"(\1)/(\2)", unit)
        )
        self.type = type
        self.min = min
        self.max = max
        self.boundaries = boundaries
        self.default = default
        self.symbol = symbol
        self.definition = (
            definition if definition is None else " ".join(definition.split())
        )
        self.value = _parse_value(
            val, self.type, self.unit, (self.min, self.max), self.name
        )
        self.model = model  # the TrnsysModel this TypeVariable belongs to.

    @classmethod
    def from_tag(cls, tag, model=None):
        """Class method to create a TypeVariable from an XML tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
            model (TrnsysModel): The model.
        """
        role = tag.find("role").text
        val = tag.find("default").text
        try:
            val = float(val)
        except ValueError:
            # could not convert string to float.
            if val == "STEP":
                val = 1
                # Todo: figure out better logic when default value is 'STEP'
            elif val == "START":
                val = 1
            elif val == "STOP":
                val = 8760
        _type = parse_type(tag.find("type").text)
        attr = {attr.name: attr.text for attr in tag if isinstance(attr, Tag)}
        attr.update({"model": model})
        if role == "parameter":
            return Parameter(_type(val), **attr)
        elif role == "input":
            return Input(_type(val), **attr)
        elif role == "output":
            return Output(_type(val), **attr)
        elif role == "derivative":
            return Derivative(_type(val), **attr)
        else:
            raise NotImplementedError(
                'The role "{}" is not yet ' "supported.".format(role)
            )

    def __float__(self):
        """Return magnitude of self."""
        return self.value.m

    def __int__(self):
        """Return int(self)."""
        return int(self.value.m)

    def __mul__(self, other):
        """Return self * other."""
        return float(self) * other

    def __add__(self, other):
        """Return self + other."""
        return float(self) + other

    def __sub__(self, other):
        """Return self - other."""
        return float(self) - other

    def _parse_types(self):
        for attr, value in self.__dict__.items():
            if attr in ["default", "max", "min"]:
                parsed_value = _parse_value(
                    value, self.type, self.unit, (self.min, self.max)
                )
                self.__setattr__(attr, parsed_value)
            if attr in ["order"]:
                self.__setattr__(attr, int(value))

    def copy(self):
        """TypeVariable: Make a copy of :attr:`self`."""
        new_self = copy.copy(self)
        return new_self

    @property
    def is_connected(self):
        """Whether or not this TypeVariable is connected to another TypeVariable.

        Checks if self is in any keys
        """
        return self.predecessor is not None

    @property
    def predecessor(self):
        """Other TypeVariable from which this Input TypeVariable is connected.

        Predecessors
        """
        if len(self.model.UNIT_GRAPH) == 0:
            return None
        predecessors = []
        for pre in self.model.UNIT_GRAPH.predecessors(self.model):
            for key in self.model.UNIT_GRAPH[pre][self.model]:
                if self in key:
                    u, v = key
                    predecessors.append(u)
        if len(predecessors) > 1:
            raise Exception(f"An Input cannot have {predecessors} predecessors")
        elif predecessors:
            return next(iter(predecessors))
        else:
            return None

    @property
    def idx(self):
        """Get the 0-based variable index of self."""
        ordered_dict = collections.OrderedDict(
            (
                standardize_name(self.model._meta.variables[attr].name),
                [self.model._meta.variables[attr], 0],
            )
            for attr in sorted(
                filter(
                    lambda kv: isinstance(
                        self.model._meta.variables[kv], self.__class__
                    )
                    and self.model._meta.variables[kv]._iscyclebase is False,
                    self.model._meta.variables,
                ),
                key=lambda key: self.model._meta.variables[key].order,
            )
            if not self.model._meta.variables[attr]._iscyclebase
        )
        i = 0
        for key, value in ordered_dict.items():
            value[1] = i
            i += 1

        return ordered_dict[standardize_name(self.name)][1]

    @property
    def one_based_idx(self):
        """Get the 1-based variable index of self such as it appears in Trnsys."""
        return self.idx + 1

    def connect_to(self, other, link_style_kwargs=None):
        """Connect a single TypeVariable to TypeVariable `other`.

        Important:
            Keep in mind that since python traditionally uses 0-based indexing,
            the same logic is used in this package even though TRNSYS uses
            traditionally 1-based indexing. The package will internally handle
            the 1-based index in the output *.dck* file.

        Examples:
            Connect two :class:`TypeVariable` objects together

            >>> pipe_1.outputs['Outlet_Air_Temperature'].connect_to(
            >>>     other=pipe2.intputs['Inlet_Air_Temperature']
            >>> )

        Args:
            other (TypeVariable): The other object.

        Raises:
            TypeError: When trying to connect to anything other than a
                :class:`TrnsysModel`.
        """
        if link_style_kwargs is None:
            link_style_kwargs = {}
        if not isinstance(other, TypeVariable):
            raise TypeError("Only `TypeVariable` objects can be connected together")

        u = self
        v = other

        loc = link_style_kwargs.pop("loc", "best")
        self.model.UNIT_GRAPH.add_edge(
            u_for_edge=self.model,
            v_for_edge=other.model,
            key=(u, v),
            LinkStyle=LinkStyle(self.model, other.model, loc=loc, **link_style_kwargs),
        )

    def __repr__(self):
        """Return repr(self)."""
        try:
            return (
                f"{self.name}; units={self.unit}; "
                f"value={self.value:~P}\n{self.definition}"
            )
        except Exception:
            return (
                f"{self.name}; units={self.unit}; value={self.value}\n"
                f"{self.definition}"
            )


class Parameter(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to parameters."""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to parameters."""
        super().__init__(val, **kwargs)

        self._parse_types()


class Input(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to inputs."""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to inputs."""
        super().__init__(val, **kwargs)

        self._parse_types()


class InitialInputValue(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to Initial Input Values."""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to inputs."""
        super().__init__(val, **kwargs)

        self._parse_types()


class Output(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to outputs."""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to outputs."""
        super().__init__(val, **kwargs)

        self._parse_types()

    @property
    def is_connected(self) -> bool:
        """Return True of self has any successor."""
        return len(self.successors) > 0

    @property
    def successors(self):
        """Other TypeVariables to which this TypeVariable is connected. Successors."""
        successors = []
        for suc in self.model.UNIT_GRAPH.successors(self.model):
            for key in self.model.UNIT_GRAPH[self.model][suc]:
                if self in key:
                    u, v = key
                    successors.append(v)
        return successors


class Derivative(TypeVariable):
    """Derivatives class.

    the DERIVATIVES for a given :class:`TrnsysModel` specify initial values,
    such as the initial temperatures of various nodes in a thermal storage tank
    or the initial zone temperatures in a multi zone building.
    """

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to derivatives."""
        super().__init__(val, **kwargs)

        self._parse_types()
