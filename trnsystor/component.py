"""Component module."""
import itertools
from abc import ABCMeta, abstractmethod

import networkx as nx
from bs4 import Tag
from shapely.geometry import Point

from trnsystor.canvas import StudioCanvas
from trnsystor.linkstyle import LinkStyle
from trnsystor.studio import StudioHeader
from trnsystor.utils import affine_transform


class Component(metaclass=ABCMeta):
    """Component class.

    Base class for Trnsys elements that interact with the Studio.
    :class:`TrnsysModel`,  :class:`ConstantCollection` and
    :class:`EquationCollection` implement this class.
    """

    INIT_UNIT_NUMBER = itertools.count(start=1)
    STUDIO_CANVAS = StudioCanvas()
    UNIT_GRAPH = nx.MultiDiGraph()

    def __init__(self, *args, **kwargs):
        """Initialize class.

        Args:
            name (str): Name of the component.
            meta (MetaData): MetaData associated with this component.
        """
        super().__init__(*args)
        self._unit = next(Component.INIT_UNIT_NUMBER)
        self.name = kwargs.pop("name")
        self._meta = kwargs.pop("meta", None)
        self.studio = StudioHeader.from_component(self)
        self.UNIT_GRAPH.add_node(self)

    def __del__(self):
        """Delete self."""
        if self in self.UNIT_GRAPH:
            self.UNIT_GRAPH.remove_node(self)

    def __hash__(self):
        """Return hash(self)."""
        return self.unit_number

    def __eq__(self, other):
        """Return self == other."""
        if isinstance(other, self.__class__):
            return self.unit_number == other.unit_number
        else:
            return self.unit_number == other

    def copy(self):
        """Return copy of self."""
        pass

    @property
    def link_styles(self):
        """Return :class:`LinkStyles` of self."""
        return [
            data["LinkStyle"]
            for u, v, key, data in self.UNIT_GRAPH.edges(keys=True, data=True)
        ]

    def set_canvas_position(self, pt, trnsys_coords=False):
        """Set position of self in the canvas.

        Use cartesian coordinates: origin 0,0 is at bottom-left.

        Hint:
            The Studio Canvas origin corresponds to the top-left of the canvas.
            The x coordinates increase from left to right, while the y
            coordinates increase from top to bottom.

            * top-left = "* $POSITION 0 0"
            * bottom-left = "* $POSITION 0 2000"
            * top-right = "* $POSITION 2000" 0
            * bottom-right = "* $POSITION 2000 2000"

            For convenience, users should deal with cartesian coordinates.
            trnsystor will deal with the transformation.

        Args:
            pt (Point or 2-tuple): The Point geometry or a tuple of (x, y)
                coordinates.
            trnsys_coords (bool): Set to True of ``pt`` is given in Trnsys Studio
                coordinates: origin 0,0 is at top-left.
        """
        if not isinstance(pt, Point):
            pt = Point(*pt)
        if trnsys_coords:
            pt = affine_transform(pt)
        if pt.within(self.STUDIO_CANVAS.bbox):
            self.studio.position = pt
        else:
            raise ValueError(
                "Can't set canvas position {} because it falls outside "
                "the bounds of the studio canvas size".format(pt)
            )

    def set_component_layer(self, layers):
        """Change the layer of self. Pass a list to change multiple layers."""
        if isinstance(layers, str):
            layers = [layers]
        self.studio.layer = layers

    @property
    def unit_number(self) -> int:
        """Return the model's unit number (unique)."""
        return self._unit

    @property
    def type_number(self) -> int:
        """Return the model's type number, eg.: ``104`` for Type104."""
        return int(
            self._meta.type
            if not isinstance(self._meta.type, Tag)
            else self._meta.type.text
        )

    @property
    def unit_name(self) -> str:
        """Return the model's unit name, eg.: 'Type104'."""
        return "Type{}".format(self.type_number)

    @property
    def model(self) -> str:
        """Return the path of this model's proforma."""
        try:
            model = self._meta.model
        except AttributeError:
            return None
        else:
            return model if not isinstance(model, Tag) else model.text

    @property
    def inputs(self):
        """InputCollection: returns the model's inputs."""
        return self._get_inputs()

    @property
    def outputs(self):
        """OutputCollection: returns the model's outputs."""
        return self._get_outputs()

    @property
    def centroid(self):
        """Point: Returns the model's center Point()."""
        return self.studio.position

    @abstractmethod
    def _get_inputs(self):
        """Sorts by order number and resolves cycles each time it is called."""
        pass

    @abstractmethod
    def _get_outputs(self):
        """Sorts by order number and resolves cycles each time it is called."""
        pass

    def set_link_style(
        self, other, loc="best", color="#1f78b4", linestyle="-", linewidth=1, path=None
    ):
        """Set outgoing link styles between self and other.

        Args:
            other (Component): The destination model.
            loc (str or tuple): loc (str): The location of the anchor. The
                strings 'top-left', 'top-right', 'bottom-left', 'bottom-right'
                place the anchor point at the corresponding corner of the
                :class:`TrnsysModel`. The strings 'top-center', 'center-right',
                'bottom-center', 'center-left' place the anchor point at the
                edge of the corresponding :class:`TrnsysModel`. The string
                'best' places the anchor point at the location, among the eight
                locations defined so far, with the shortest distance with the
                destination :class:`TrnsysModel` (other). The location can also
                be a 2-tuple giving the coordinates of the origin
                :class:`TrnsysModel` and the destination :class:`TrnsysModel`.
            color (str or tuple): The color of the line. Accepts any matplotlib
                color. You can specify colors in many ways, including full names
                (‘green’), hex strings (‘#008000’), RGB or RGBA tuples
                ((0,1,0,1)) or grayscale intensities as a string (‘0.8’).
            linestyle (str): Possible values: '-' or 'solid', '--' or 'dashed',
                '-.' or 'dashdot', ':' or 'dotted', '-.' or 'dashdotdot'.
            linewidth (float): The width of the line in points.
            path (LineString or MultiLineString, optional): The path of the
                link.
        """
        if other is None:
            raise ValueError("Other is None")

        style = LinkStyle(
            self,
            other,
            loc,
            path=path,
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
        )
        if self.UNIT_GRAPH.has_edge(self, other):
            for key in self.UNIT_GRAPH[self][other]:
                self.UNIT_GRAPH[self][other][key]["LinkStyle"] = style
        else:
            raise KeyError(
                "Trying to set a LinkStyle on a non-existent connection. "
                f"Make sure to connect {self} using '.connect_to()'"
            )

    def connect_to(self, other, mapping=None, link_style_kwargs=None):
        """Connect the outputs of :attr:`self` to the inputs of :attr:`other`.

        Important:
            Keep in mind that since python traditionally uses 0-based indexing,
            the same logic is used in this package even though TRNSYS uses
            traditionally 1-based indexing. The package will internally handle
            the 1-based index in the output *.dck* file.

        Examples:
            Connect two :class:`TrnsysModel` objects together by creating a
            mapping of the outputs of pipe_1 to the intputs of pipe_2. In this
            example we connect output_0 of pipe_1 to input_0 of pipe_2 and
            output_1 of pipe_1 to input_1 of pipe_2:

            >>> pipe_1.connect_to(pipe_2, mapping={0:0, 1:1})

            The same can be acheived using input/output names.

            >>> pipe_1.connect_to(pipe_2, mapping={'Outlet_Air_Temperature':
            >>> 'Inlet_Air_Temperature', 'Outlet_Air_Humidity_Ratio':
            >>> 'Inlet_Air_Humidity_Ratio'})

        Args:
            other (Component): The other object
            mapping (dict): Mapping of output to intput numbers (or names)
            link_style_kwargs (dict, optional): dict of :class:`LinkStyle` parameters

        Raises:
            TypeError: A `TypeError is raised when trying to connect to anything
                other than a :class:`TrnsysModel`.
        """
        if link_style_kwargs is None:
            link_style_kwargs = {}
        if not isinstance(other, Component):
            raise TypeError("Only `Component` objects can be connected together")
        if mapping is None:
            raise NotImplementedError(
                "Automapping is not yet implemented. " "Please provide a mapping dict"
            )
            # Todo: Implement automapping logic here
        else:
            # loop over the mapping and add edge to UNIT_GRAPH.
            for from_self, to_other in mapping.items():
                u = self.outputs[from_self]
                v = other.inputs[to_other]
                if self.UNIT_GRAPH.has_edge(self, other, (u, v)):
                    msg = (
                        'The output "{}: {}" of model "{}" is already '
                        'connected to the input "{}: {}" of model "{}"'.format(
                            u.idx,
                            u.name,
                            u.model.name,
                            v.idx,
                            v.name,
                            v.model.name,
                        )
                    )
                    raise ValueError(msg)
                else:
                    loc = link_style_kwargs.pop("loc", "best")
                    self.UNIT_GRAPH.add_edge(
                        u_for_edge=self,
                        v_for_edge=other,
                        key=(u, v),
                        LinkStyle=LinkStyle(self, other, loc=loc, **link_style_kwargs),
                    )

    @property
    def successors(self):
        """Other objects to which this TypeVariable is connected. Successors."""
        return self.UNIT_GRAPH.successors(self)

    @property
    def is_connected(self):
        """Whether or not this Component is connected to another TypeVariable.

        Connected to or connected by.
        """
        return any([len(list(self.predecessors)) > 0, len(list(self.successors)) > 0])

    @property
    def predecessors(self):
        """Other objects from which this TypeVariable is connected. Predecessors."""
        return self.UNIT_GRAPH.predecessors(self)

    def invalidate_connections(self):
        """Iterate over successors and predecessors and remove the edges.

        Todo: restore paths in self.studio_canvas.grid
        """
        edges = []
        for nbr in self.UNIT_GRAPH.successors(self):
            edges.append((self, nbr))
        for nbr in self.UNIT_GRAPH.predecessors(self):
            edges.append((nbr, self))
        while edges:
            edge = edges.pop()
            self.UNIT_GRAPH.remove_edge(*edge)
            if self.UNIT_GRAPH.has_edge(*edge):
                edges.append(edge)

    def _to_deck(self):
        """Return deck representation of self."""
        pass
