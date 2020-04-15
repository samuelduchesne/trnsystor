import collections
import copy
import datetime
import itertools
import logging as lg
import re
import tempfile
from abc import ABCMeta, abstractmethod

import networkx as nx
import numpy as np
import tabulate
from bs4 import BeautifulSoup, Tag
from matplotlib.colors import colorConverter
from pandas import to_datetime
from path import Path
from pint.quantity import _Quantity
from shapely.geometry import Point, LineString, MultiLineString, MultiPoint, box
from sympy import Symbol, Expr

from pyTrnsysType.utils import (
    get_int_from_rgb,
    _parse_value,
    parse_type,
    standerdized_name,
    redistribute_vertices,
    get_rgb_from_int,
    affine_transform,
    TypeVariableSymbol,
    print_my_latex,
)


class MetaData(object):
    def __init__(
        self,
        object=None,
        author=None,
        organization=None,
        editor=None,
        creationDate=None,
        modifictionDate=None,
        mode=None,
        validation=None,
        icon=None,
        type=None,
        maxInstance=None,
        keywords=None,
        details=None,
        comment=None,
        variables=None,
        plugin=None,
        variablesComment=None,
        cycles=None,
        source=None,
        externalFiles=None,
        compileCommand=None,
        model=None,
        **kwargs,
    ):
        """General information that is associated with a :class:`TrnsysModel`.
        This information is contained in the General Tab of the Proforma.

        Args:
            object (str): A generic name describing the component model.
            author (str): The name of the person who wrote the model.
            organization (str): The name of organization with which the Author
                is affiliated.
            editor (str): Often, the person creating the Simulation Studio
                Proforma is not the original author and so the name of the
                Editor may also be important.
            creationDate (str): This is the date of when the model was first
                written.
            modifictionDate (str): This is the date when the Proforma was mostly
                recently revised.
            mode (int): 1-Detailed, 2-Simplified, 3-Empirical, 4- Conventional
            validation (int): Determine the type of validation that was
                performed on this model. This can be 1-qualitative, 2-numerical,
                3-analytical, 4-experimental and 5-‘in assembly’ meaning that it
                was verified as part of a larger system which was verified.
            icon (Path): Path to the icon.
            type (int): The type number.
            maxInstance (int): The maximum number of instances this type can be
                used.
            keywords (str): keywords associated with this model.
            details (str): The detailed description contains an explanation of
                the model including a mathematical description of the model
            comment (str): The text entered here will appear as a comment in the
                TRNSYS input file. This allows to attach important information
                about the component to all its users, including users who prefer
                to edit the input file with a text editor. This text should be
                short, to avoid overloading the input file.
            variables (dict, optional): a list of :class:`TypeVariable`.
            plugin (Path): The plug-in path contains the path to the an external
                application which will be executed to modify component
                properties instead of the classical properties window.
            variablesComment (str): #todo What is this?
            cycles (list, optional): List of TypeCycle.
            source (Path): Path of the source code.
            externalFiles (ExternalFileCollection): A class handling
                ExternalFiles for this object.
            compileCommand (str): Command used to recompile this type.
            model (Path): Path of the xml or tmf file.
            **kwargs:
        """
        self.compileCommand = compileCommand
        self.object = object
        self.author = author
        self.organization = organization
        self.editor = editor
        self.creationDate = creationDate
        self.modifictionDate = modifictionDate
        self.mode = mode
        self.validation = validation
        self.icon = icon
        self.type = type
        self.maxInstance = maxInstance
        self.keywords = keywords
        self.details = details
        self.comment = comment
        self.variablesComment = variablesComment
        self.plugin = plugin
        self.cycles = cycles
        self.source = source
        self.model = model

        self.variables = variables
        self.external_files = externalFiles

        self.check_extra_tags(kwargs)

    @classmethod
    def from_tag(cls, tag, **kwargs):
        """Class method used to create a TrnsysModel from a xml Tag

        Args:
            tag (Tag): The XML tag with its attributes and contents.
            **kwargs:
        """
        meta_args = {
            child.name: child.__copy__()
            for child in tag.children
            if isinstance(child, Tag)
        }
        xml_args = {
            child.name: child.prettify()
            for child in tag.children
            if isinstance(child, Tag)
        }
        meta_args.update(kwargs)
        return cls(**{attr: meta_args[attr] for attr in meta_args})

    def check_extra_tags(self, kwargs):
        """Detect extra tags in the proforma and warn.

        Args:
            kwargs (dict): dictionary of extra keyword-arguments that would be
                passed to the constructor.
        """
        if kwargs:
            msg = (
                "Unknown tags have been detected in this proforma: {}.\nIf "
                "you wish to continue, the behavior of the object might be "
                "affected. Please contact the package developers or submit "
                "an issue.\n Do you wish to continue anyways?".format(
                    ", ".join(kwargs.keys())
                )
            )
            shall = input("%s (y/N) " % msg).lower() == "y"
            if not shall:
                raise NotImplementedError()

    def __getitem__(self, item):
        """eg.: self[item] :param item:

        Args:
            item:
        """
        return getattr(self, item)

    @classmethod
    def from_xml(cls, xml, **kwargs):
        """
        Args:
            xml:
            **kwargs:
        """
        xml_file = Path(xml)
        with open(xml_file) as xml:
            soup = BeautifulSoup(xml, "xml")
            my_objects = soup.findAll("TrnsysModel")
            for trnsystype in my_objects:
                kwargs.pop("name", None)
                meta = cls.from_tag(trnsystype, **kwargs)
                return meta


class ExternalFile(object):
    logic_unit = itertools.count(start=30)
    _logic_unit = itertools.count(start=30)

    def __init__(self, question, default, answers, parameter, designate):
        """
        Args:
            question (str):
            default (str):
            answers (list of str):
            parameter (str):
            designate (bool): If True, the external files are assigned to
                logical unit numbers from within the TRNSYS input file. Files
                that are assigned to a logical unit number using a DESIGNATE
                statement will not be opened by the TRNSYS kernel.
        """
        self.designate = designate
        self.parameter = parameter
        self.answers = [Path(answer) for answer in answers]
        self.default = Path(default)
        self.question = question

        self.logical_unit = next(self._logic_unit)

        self.value = self.default

    @classmethod
    def from_tag(cls, tag):
        """
        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        question = tag.find("question").text
        default = tag.find("answer").text
        answers = [
            tag.text for tag in tag.find("answers").children if isinstance(tag, Tag)
        ]
        parameter = tag.find("parameter").text
        designate = tag.find("designate").text
        return cls(question, default, answers, parameter, designate)


class ExternalFileCollection(collections.UserDict):
    """A collection of :class:`ExternalFile` objects"""

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super().__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """
        Args:
            key:
            value:
        """
        if isinstance(value, ExternalFile):
            """if a ExternalFile is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, (str, Path)):
            """a str, or :class:Path is passed"""
            value = Path(value)
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                "Cannot set a value of type {} in this "
                "ExternalFileCollection".format(type(value))
            )

    @classmethod
    def from_dict(cls, dictionary):
        """Construct an :class:`~ExternalFileCollection` from a dict of
        :class:`~ExternalFile` objects with the object's id as a key.

        Args:
            dictionary (dict): The dict of {key: :class:`~ExternalFile`}
        """
        item = cls()
        for key in dictionary:
            # self.parameters[key] = ex_file.logical_unit
            named_key = standerdized_name(dictionary[key].question)
            item.__setitem__(named_key, dictionary[key])
        return item

    def _to_deck(self):
        """Returns the string representation for the external files (.dck)"""
        if self:
            head = "*** External files\n"
            v_ = (
                ("ASSIGN", '"{}"'.format(ext_file.value), ext_file.logical_unit)
                for ext_file in self.values()
            )
            core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")

            return str(head) + str(core)
        else:
            return ""


class ComponentCollection(collections.UserList):
    """A class that handles collections of components, eg.; TrnsysModels,
    EquationCollections and ConstantCollections

    Get a component from a ComponentCollection using either the component's
    unit numer or its full name.

    Examples:
        >>> from pyTrnsysType.trnsymodel import ComponentCollection
        >>> cc = ComponentCollection()
        >>> cc.update({tank_type: tank_type})
        >>> cc['Storage Tank; Fixed Inlets, Uniform Losses']._unit = 1
        >>> cc[1]
        Type146: Single Speed Fan/Blower
        >>> cc['Single Speed Fan/Blower']
        Type146: Single Speed Fan/Blower
    """

    @property
    def iloc(self):
        return dict({item.unit_number: item for item in self.data})

    @property
    def loc(self):
        return dict({item: item for item in self.data})


class StudioCanvas:
    # TODO: Document class
    def __init__(self, width=150, height=150):
        self._grid_valid = True
        self._grid = None
        self.width = width
        self.height = height

    @property
    def bbox(self):
        """The :class:`shapely.geometry.geo.box` representation of the studio canvas"""
        return box(0, 0, self.width, self.height)

    @property
    def grid_is_valid(self):
        if self._grid_valid:
            return True
        else:
            return False

    @property
    def grid(self):
        """The two-dimensional grid graph of the studio canvas"""
        if self.grid_is_valid and self._grid is not None:
            return self._grid
        else:
            self._grid = nx.grid_2d_graph(self.width, self.height)
            return self._grid

    def invalidate_grid(self):
        self._grid_valid = False

    def resize_canvas(self, width, height):
        """Change the canvas size.

        TODO: Handle grid when canvas size is changed (e.g used paths)

        Args:
            width (int): new width.
            height (int): new height.
        """
        self.width = width
        self.height = height
        self.invalidate_grid()

    def shortest_path(self, u, v, donotcross=True):
        """Returns the shortest path on the canvas grid. If dotnotcross=True,
        the edges along the path will be removed from the canvas grid graph in order

        Args:
            u (Point): The *from* Point geometry.
            v (Point): The *to* Point geometry.
            dotnotcross (bool): If true, this path will not be crossed by other paths.

        Returns:
            (LineString): The path from u to v along the studio graph
        """
        shortest_path = nx.shortest_path(self.grid, (u.x, u.y), (v.x, v.y))
        if donotcross:
            edges = self.grid.edges(shortest_path)
            for edge in edges:
                self.grid.remove_edges_from(edge)
        # create linestring and simplify to unit and return
        try:
            return LineString(shortest_path).simplify(1)
        except ValueError:
            return shortest_path


class Component(metaclass=ABCMeta):
    """Base class for Trnsys elements that interact with the Studio.
    :class:`TrnsysModel`,  :class:`ConstantCollection` and
    :class:`EquationCollection` implement this class."""

    initial_unit_number = itertools.count(start=1)
    studio_canvas = StudioCanvas()
    unit_graph = nx.MultiDiGraph()

    def __init__(self, name, meta):
        """Initialize a Component with the following parameters:

        Args:
            name (str): Name of the component.
            meta (MetaData): MetaData associated with this component.
        """
        self._unit = next(TrnsysModel.initial_unit_number)
        self.name = name
        self._meta = meta
        self.studio = StudioHeader.from_component(self)
        self.unit_graph.add_node(self)

    def __del__(self):
        self.unit_graph.remove_node(self)

    def __hash__(self):
        return self.unit_number

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.unit_number == other.unit_number
        else:
            return self.unit_number == other

    @property
    def link_styles(self):
        return [
            data["LinkStyle"]
            for u, v, key, data in self.unit_graph.edges(keys=True, data=True)
        ]

    def set_canvas_position(self, pt, trnsys_coords=False):
        """Set position of self in the canvas. Use cartesian coordinates: origin
        0,0 is at bottom-left.

        Hint:
            The Studio Canvas origin corresponds to the top-left of the canvas.
            The x coordinates increase from left to right, while the y
            coordinates increase from top to bottom.

            * top-left = "* $POSITION 0 0"
            * bottom-left = "* $POSITION 0 2000"
            * top-right = "* $POSITION 2000" 0
            * bottom-right = "* $POSITION 2000 2000"

            For convenience, users should deal with cartesian coordinates.
            pyTrnsysType will deal with the transformation.

        Args:
            pt (Point or 2-tuple): The Point geometry or a tuple of (x, y)
                coordinates.
            trnsys_coords:
        """
        if not isinstance(pt, Point):
            pt = Point(*pt)
        if trnsys_coords:
            pt = affine_transform(pt)
        if pt.within(self.studio_canvas.bbox):
            self.studio.position = pt
        else:
            raise ValueError(
                "Can't set canvas position {} because it falls outside "
                "the bounds of the studio canvas size".format(pt)
            )

    def set_component_layer(self, layers):
        """Change the component's layer. Pass a list to change multiple layers

        Args:
            layers (str or list):
        """
        if isinstance(layers, str):
            layers = [layers]
        self.studio.layer = layers

    @property
    def unit_number(self):
        """int: Returns the model's unit number (unique)"""
        return int(self._unit)

    @property
    def type_number(self):
        """int: Returns the model's type number, eg.: 104 for Type104"""
        return int(
            self._meta.type
            if not isinstance(self._meta.type, Tag)
            else self._meta.type.text
        )

    @property
    def unit_name(self):
        """str: Returns the model's unit name, eg.: 'Type104'"""
        return "Type{}".format(self.type_number)

    @property
    def model(self):
        """str: The path of this model's proforma"""
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
        """inputs getter. Sorts by order number and resolves cycles each time it
        is called
        """
        pass

    @abstractmethod
    def _get_outputs(self):
        """outputs getter. Sorts by order number and resolves cycles each time
        it is called
        """
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
        if self.unit_graph.has_edge(self, other):
            for key in self.unit_graph[self][other]:
                self.unit_graph[self][other][key]["LinkStyle"] = style
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
            # loop over the mapping and assign :class:`TypeVariable` to
            # `_connected_to` attribute.
            for from_self, to_other in mapping.items():
                u = self.outputs[from_self]
                v = other.inputs[to_other]
                if self.unit_graph.has_edge(self, other, (u, v)):
                    msg = (
                        'The output "{}: {}" of model "{}" is already '
                        'connected to the input "{}: {}" of model "{}"'.format(
                            u.idx, u.name, u.model.name, v.idx, v.name, v.model.name,
                        )
                    )
                    raise ValueError(msg)
                else:
                    loc = link_style_kwargs.pop("loc", "best")
                    self.unit_graph.add_edge(
                        u_for_edge=self,
                        v_for_edge=other,
                        key=(u, v),
                        LinkStyle=LinkStyle(self, other, loc=loc, **link_style_kwargs),
                    )

    @property
    def successors(self):
        """Other objects to which this TypeVariable is connected. successors"""
        return self.unit_graph.successors(self)

    @property
    def predecessors(self):
        """Other objects from which this TypeVariable is connected. Predecessors"""
        return self.unit_graph.predecessors(self)

    def invalidate_connections(self):
        """iterate over inputs/outputs and force :attr:`_connected_to` to
        None.

        Todo: restore paths in self.studio_canvas.grid
        """
        edges = []
        for nbr in self.unit_graph.successors(self):
            edges.append((self, nbr))
        for nbr in self.unit_graph.predecessors(self):
            edges.append((nbr, self))
        has_edge = True
        while edges:
            edge = edges.pop()
            self.unit_graph.remove_edge(*edge)
            if self.unit_graph.has_edge(*edge):
                edges.append(edge)

    def copy(self, invalidate_connections=True):
        """Returns a copy of the Component. The copy will be translated 10 units to
        the right.

        Args:
            invalidate_connections (bool): If True, connections to other Components
                will be reset.
        """
        new = copy.deepcopy(self)
        new._unit = next(new.initial_unit_number)
        new.unit_graph.add_node(new)
        if invalidate_connections:
            new.invalidate_connections()
        from shapely.affinity import translate

        pt = translate(self.centroid, 10, 0)
        new.set_canvas_position(pt)
        return new


class TrnsysModel(Component):
    def __init__(self, meta, name):
        """Main Class for holding TRNSYS components. Alone, this __init__ method
        does not do much. See the :func:`from_xml` class method for the official
        constructor of this class.

        Args:
            meta (MetaData): A class containing the model's metadata.
            name (str): A user-defined name for this model.
        """
        super().__init__(name, meta)

    def __repr__(self):
        """str: The String representation of this object."""
        return "[{}]Type{}: {}".format(self.unit_number, self.type_number, self.name)

    @classmethod
    def from_xml(cls, xml, **kwargs):
        """Class method to create a :class:`TrnsysModel` from an xml string.

        Examples:
            Simply pass the xml path to the constructor.

            >>> from pyTrnsysType import TrnsysModel
            >>> fan1 = TrnsysModel.from_xml("Tests/input_files/Type146.xml")

        Args:
            xml (str or Path): The path of the xml file.
            **kwargs:

        Returns:
            TrnsysType: The TRNSYS model.
        """
        xml_file = Path(xml)
        with open(xml_file) as xml:
            all_types = []
            soup = BeautifulSoup(xml, "xml")
            my_objects = soup.findAll("TrnsysModel")
            for trnsystype in my_objects:
                t = cls._from_tag(trnsystype, **kwargs)
                t._meta.model = xml_file
                t.studio = StudioHeader.from_component(t)
                all_types.append(t)
            return all_types[0]

    @property
    def derivatives(self):
        """VariableCollection: returns the model's derivatives"""
        return self._get_derivatives()

    @property
    def initial_input_values(self):
        """VariableCollection: returns the model's initial input values."""
        return self._get_initial_input_values()

    @property
    def parameters(self):
        """ParameterCollection: returns the model's parameters."""
        return self._get_parameters()

    @property
    def external_files(self):
        """ExternalFileCollection: returns the model's external files"""
        return self._get_external_files()

    @property
    def anchor_points(self):
        """dict: Returns the 8-AnchorPoints as a dict with the anchor point
        location ('top-left', etc.) as a key.
        """
        return AnchorPoint(self).anchor_points

    @property
    def reverse_anchor_points(self):
        return AnchorPoint(self).reverse_anchor_points

    @classmethod
    def _from_tag(cls, tag, **kwargs):
        """Class method to create a :class:`TrnsysModel` from a tag

        Args:
            tag (Tag): The XML tag with its attributes and contents.
            **kwargs:

        Returns:
            TrnsysModel: The TRNSYS model.
        """
        name = kwargs.pop("name", tag.find("object").text)
        meta = MetaData.from_tag(tag, **kwargs)

        model = cls(meta, name)
        type_vars = [
            TypeVariable.from_tag(tag, model=model)
            for tag in tag.find("variables")
            if isinstance(tag, Tag)
        ]
        type_cycles = CycleCollection(
            TypeCycle.from_tag(tag)
            for tag in tag.find("cycles").children
            if isinstance(tag, Tag)
        )
        model._meta.variables = {id(var): var for var in type_vars}
        model._meta.cycles = type_cycles
        file_vars = (
            [
                ExternalFile.from_tag(tag)
                for tag in tag.find("externalFiles").children
                if isinstance(tag, Tag)
            ]
            if tag.find("externalFiles")
            else None
        )
        model._meta.external_files = (
            {id(var): var for var in file_vars} if file_vars else None
        )

        model._get_inputs()
        model._get_outputs()
        model._get_parameters()
        model._get_external_files()

        return model

    def _get_initial_input_values(self):
        """initial input values getter"""
        try:
            self._resolve_cycles("input", Input)
            input_dict = self._get_ordered_filtered_types(Input, "variables")
            # filter out cyclebases
            input_dict = {
                k: v for k, v in input_dict.items() if v._iscyclebase == False
            }
            return InitialInputValuesCollection.from_dict(input_dict)
        except:
            return InitialInputValuesCollection()

    def _get_inputs(self):
        """inputs getter. Sorts by order number and resolves cycles each time it
        is called
        """
        try:
            self._resolve_cycles("input", Input)
            input_dict = self._get_ordered_filtered_types(Input, "variables")
            # filter out cyclebases
            input_dict = {
                k: v for k, v in input_dict.items() if v._iscyclebase == False
            }
            return InputCollection.from_dict(input_dict)
        except:
            return InputCollection()

    def _get_outputs(self):
        """outputs getter. Sorts by order number and resolves cycles each time
        it is called
        """
        # output_dict = self._get_ordered_filtered_types(Output)
        try:
            self._resolve_cycles("output", Output)
            output_dict = self._get_ordered_filtered_types(Output, "variables")
            # filter out cyclebases
            output_dict = {
                k: v for k, v in output_dict.items() if v._iscyclebase == False
            }
            return OutputCollection.from_dict(output_dict)
        except TypeError:
            return OutputCollection()

    def _get_parameters(self):
        """parameters getter. Sorts by order number and resolves cycles each
        time it is called
        """
        self._resolve_cycles("parameter", Parameter)
        param_dict = self._get_ordered_filtered_types(Parameter, "variables")
        # filter out cyclebases
        param_dict = {k: v for k, v in param_dict.items() if v._iscyclebase == False}
        return ParameterCollection.from_dict(param_dict)

    def _get_derivatives(self):
        self._resolve_cycles("derivative", Derivative)
        deriv_dict = self._get_ordered_filtered_types(Derivative, "variables")
        # filter out cyclebases
        deriv_dict = {k: v for k, v in deriv_dict.items() if v._iscyclebase == False}
        return DerivativesCollection.from_dict(deriv_dict)

    def _get_external_files(self):
        if self._meta.external_files:
            ext_files_dict = dict(
                (attr, self._meta["external_files"][attr])
                for attr in self._get_filtered_types(ExternalFile, "external_files")
            )
            return ExternalFileCollection.from_dict(ext_files_dict)

    def _get_ordered_filtered_types(self, class_name, store):
        """Returns an ordered dict of :class:`TypeVariable` filtered by
        *class_name* and ordered by their order number attribute.

        Args:
            class_name: Name of TypeVariable to filer: Choices are :class:`Input`,
                :class:`Output`, :class:`Parameter`, :class:`Derivative`.
            store (str): Attribute name from :class:`MetaData`. Typically, this is
                the "variables" attribute.
        """
        return collections.OrderedDict(
            (attr, self._meta[store][attr])
            for attr in sorted(
                self._get_filtered_types(class_name, store),
                key=lambda key: self._meta[store][key].order,
            )
        )

    def _get_filtered_types(self, class_name, store):
        """Returns a filter of TypeVariables from the self._meta[store] by *class_name*

        Args:
            class_name: Name of TypeVariable to filer: Choices are :class:`Input`,
                :class:`Output`, :class:`Parameter`, :class:`Derivative`.
            store (str): Attribute name from :class:`MetaData`. Typically, this is
                the "variables" attribute.
        """
        return filter(
            lambda kv: isinstance(self._meta[store][kv], class_name), self._meta[store]
        )

    def _resolve_cycles(self, type_, class_):
        """Cycle resolver. Proformas can contain parameters, inputs and ouputs
        that have a variable number of entries. This will deal with their
        creation each time the linked parameters are changed.

        Args:
            type_ (str): The name of the TypeVariable.
            class_ (TypeVariable):
        """
        output_dict = self._get_ordered_filtered_types(class_, "variables")
        cycles = {
            str(id(attr)): attr for attr in self._meta.cycles if attr.role == type_
        }
        # repeat cycle variables n times
        cycle: TypeCycle
        for _, cycle in cycles.items():
            idxs = cycle.idxs
            # get list of variables that are not cycles
            items = [
                output_dict.get(id(key))
                for key in [
                    [i for i in output_dict.values() if not i._iscycle][i] for i in idxs
                ]
            ]
            if cycle.is_question:
                n_times = []
                for cycle in cycle.cycles:
                    existing = next(
                        (
                            key
                            for key, value in output_dict.items()
                            if value.name == cycle.question
                        ),
                        None,
                    )
                    if not existing:
                        name = cycle.question
                        question_var: TypeVariable = class_(
                            val=cycle.default,
                            name=name,
                            role=cycle.role,
                            unit="-",
                            type=int,
                            dimension="any",
                            min=int(cycle.minSize),
                            max=int(cycle.maxSize),
                            order=9999999,
                            default=cycle.default,
                            model=self,
                        )
                        question_var._is_question = True
                        self._meta.variables.update({id(question_var): question_var})
                        output_dict.update({id(question_var): question_var})
                        n_times.append(question_var.value.m)
                    else:
                        n_times.append(output_dict[existing].value.m)
            else:
                n_times = [
                    list(
                        filter(
                            lambda elem: elem[1].name == cycle.paramName,
                            self._meta.variables.items(),
                        )
                    )[0][1].value.m
                    for cycle in cycle.cycles
                ]
            item: TypeVariable
            mydict = {
                key: self._meta.variables.pop(key)
                for key in dict(
                    filter(
                        lambda kv: kv[1].role == type_ and kv[1]._iscycle,
                        self._meta.variables.items(),
                    )
                )
            }
            # pop output_dict items
            [
                output_dict.pop(key)
                for key in dict(
                    filter(
                        lambda kv: kv[1].role == type_ and kv[1]._iscycle,
                        self._meta.variables.items(),
                    )
                )
            ]
            # make sure to cycle through all possible items
            items_list = list(
                zip(items, itertools.cycle(n_times))
                if len(items) > len(n_times)
                else zip(itertools.cycle(items), n_times)
            )
            for item, n_time in items_list:
                item._iscyclebase = True
                basename = item.name
                item_base = self._meta.variables.get(id(item))
                for n, _ in enumerate(range(int(n_time)), start=1):
                    existing = next(
                        (
                            key
                            for key, value in mydict.items()
                            if value.name == basename + "-{}".format(n)
                        ),
                        None,
                    )
                    item = mydict.get(existing, item_base.copy())
                    item._iscyclebase = False  # return it back to False
                    if item._iscycle:
                        self._meta.variables.update({id(item): item})
                    else:
                        item.name = basename + "-{}".format(n)
                        item.order += 1 if n_time > 1 else 0
                        item._iscycle = True
                        self._meta.variables.update({id(item): item})

    def _to_deck(self):
        """print the Input File (.dck) representation of this TrnsysModel"""
        unit_type = "UNIT {n} TYPE {m} {name}\n".format(
            n=self.unit_number, m=self.type_number, name=self.name
        )
        studio = self.studio
        params = self.parameters
        inputs = self.inputs
        initial_input_values = self.initial_input_values
        derivatives = self.derivatives
        externals = self.external_files._to_deck() if self.external_files else ""

        return (
            str(unit_type)
            + str(studio)
            + params._to_deck()
            + inputs._to_deck()
            + initial_input_values._to_deck()
            + derivatives._to_deck()
            + str(externals)
        )

    def update_meta(self, new_meta):
        """
        Args:
            new_meta:
        """
        for attr in self._meta.__dict__:
            if hasattr(new_meta, attr):
                setattr(self._meta, attr, getattr(new_meta, attr))
        tag = new_meta.variables
        type_vars = [
            TypeVariable.from_tag(tag, model=self)
            for tag in tag
            if isinstance(tag, Tag)
        ]
        tag = new_meta.cycles
        type_cycles = CycleCollection(
            TypeCycle.from_tag(tag) for tag in tag if isinstance(tag, Tag)
        )
        self._meta.variables = {id(var): var for var in type_vars}
        self._meta.cycles = type_cycles

        tag = new_meta.external_files
        if tag:
            self._meta.external_files = ExternalFileCollection.from_dict(
                {
                    id(ext): ext
                    for ext in {
                        ExternalFile.from_tag(tag)
                        for tag in tag
                        if isinstance(tag, Tag)
                    }
                }
            )

        # self._get_inputs()
        # self._get_outputs()
        # self._get_parameters()
        # self._get_external_files()

        # _meta = MetaData.from_tag([s for s in new_meta.author.parents][-1])

    def plot(self):
        import matplotlib.pyplot as plt

        G = nx.DiGraph()
        G.add_edges_from(("type", output.name) for output in self.outputs.values())
        G.add_edges_from((input.name, "type") for input in self.inputs.values())
        pos = nx.drawing.planar_layout(G, center=(50, 50))
        ax = nx.draw_networkx(
            G,
            pos,
            with_labels=True,
            edge_labels={
                ("type", output.name): output.name for output in self.outputs.values()
            },
            arrow=True,
            width=4,
        )
        plt.show()
        return ax


class TypeVariable(object):
    """
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
        """Initialize a TypeVariable with the following attributes:

        Args:
            val (int, float, _Quantity): The actual value hold by this object.
            order (str):
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
            model:
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
            model (TrnsysModel):
        """
        role = tag.find("role").text
        val = tag.find("default").text
        try:
            val = float(val)
        except:  # todo: find type of error
            # val is a string
            if val == "STEP":
                val = 1
                # Todo: figure out better logic when default value
                #  is 'STEP
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
        return self.value.m

    def __int__(self):
        return int(self.value.m)

    def __mul__(self, other):
        return float(self) * other

    def __add__(self, other):
        return float(self) + other

    def __sub__(self, other):
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
        """TypeVariable: Make a copy of :attr:`self`"""
        new_self = copy.copy(self)
        return new_self

    @property
    def is_connected(self):
        """Whether or not this TypeVariable is connected to another TypeVariable.
        Checks if self is in any keys"""
        # connected = 0
        # for nbr in self.model.unit_graph[self.model]:
        #     for key in self.model.unit_graph[self.model][nbr]:
        #         if self in key:
        #             connected += 1
        if isinstance(self, Input):
            return self.predecessor is not None
        elif isinstance(self, Output):
            return len(self.successors) > 0

    @property
    def idx(self):
        """The 0-based index of the TypeVariable"""
        ordered_dict = collections.OrderedDict(
            (
                standerdized_name(self.model._meta.variables[attr].name),
                [self.model._meta.variables[attr], 0],
            )
            for attr in sorted(
                filter(
                    lambda kv: isinstance(
                        self.model._meta.variables[kv], self.__class__
                    )
                    and self.model._meta.variables[kv]._iscyclebase == False,
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

        return ordered_dict[standerdized_name(self.name)][1]

    @property
    def one_based_idx(self):
        return self.idx + 1


class TypeCycle(object):
    def __init__(
        self,
        role=None,
        firstRow=None,
        lastRow=None,
        cycles=None,
        minSize=None,
        maxSize=None,
        paramName=None,
        question=None,
        **kwargs,
    ):
        """
        Args:
            role (str): The role of the TypeCycle. "parameter", "input",
                "output"
            firstRow:
            lastRow:
            cycles:
            minSize:
            maxSize:
            paramName:
            question:
            **kwargs:
        """
        super().__init__()
        self.role = role
        self.firstRow = firstRow
        self.lastRow = lastRow
        self.cycles = cycles
        self.minSize = minSize
        self.maxSize = maxSize
        self.paramName = paramName
        self.question = question

    @classmethod
    def from_tag(cls, tag):
        """
        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        dict_ = collections.defaultdict(list)
        for attr in filter(lambda x: isinstance(x, Tag), tag):
            if attr.name != "cycles" and not attr.is_empty_element:
                dict_[attr.name] = attr.text
            elif attr.is_empty_element:
                pass
            else:
                dict_["cycles"].extend(
                    [cls.from_tag(tag) for tag in attr if isinstance(tag, Tag)]
                )
        return cls(**dict_)

    def __repr__(self):
        return self.role + " {} to {}".format(self.firstRow, self.lastRow)

    @property
    def default(self):
        return int(self.minSize)

    @property
    def idxs(self):
        """0-based index of the TypeVariable(s) concerned with this cycle"""
        return (
            list(
                itertools.chain(
                    *(
                        range(int(cycle.firstRow) - 1, int(cycle.lastRow))
                        for cycle in self.cycles
                    )
                )
            )
            if self.cycles
            else None
        )

    @property
    def is_question(self):
        return (
            any(cycle.question is not None for cycle in self.cycles)
            if self.cycles
            else None
        )


class CycleCollection(collections.UserList):
    def __getitem__(self, key):
        """
        Args:
            key:
        """
        value = super().__getitem__(key)
        return value


class Parameter(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to parameters"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to parameters.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._connected_to = None
        self._parse_types()

    def __repr__(self):
        return "{}; units={}; value={:~P}\n{}".format(
            self.name, self.unit, self.value, self.definition
        )


class Input(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to inputs"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to inputs.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._connected_to = None
        self._parse_types()

    def __repr__(self):
        return "{}; units={}; value={:~P}\n{}".format(
            self.name, self.unit, self.value, self.definition
        )

    @property
    def predecessor(self):
        """Other TypeVariable from which this Input TypeVariable is connected.
        Predecessors
        Todo: May have to return a list
        """
        predecessors = []
        for pre in self.model.unit_graph.predecessors(self.model):
            for key in self.model.unit_graph[pre][self.model]:
                if self in key:
                    u, v = key
                    predecessors.append(u)
        if len(predecessors) > 1:
            raise Exception("An Input cannot have {predecessors} predecessors")
        elif predecessors:
            return next(iter(predecessors))
        else:
            return None


class InitialInputValue(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to Initial Input Values"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to inputs.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._connected_to = None
        self._parse_types()

    def __repr__(self):
        return "{}; units={}; value={:~P}\n{}".format(
            self.name, self.unit, self.default, self.definition
        )


class Output(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to outputs"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to outputs.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._connected_to = []
        self._parse_types()

    def __repr__(self):
        return "{}; units={}; value={:~P}\n{}".format(
            self.name, self.unit, self.value, self.definition
        )

    @property
    def successors(self):
        """Other TypeVariables to which this TypeVariable is connected. Successors"""
        successors = []
        for suc in self.model.unit_graph.successors(self.model):
            for key in self.model.unit_graph[self.model][suc]:
                if self in key:
                    u, v = key
                    successors.append(v)
        return successors


class Derivative(TypeVariable):
    """the DERIVATIVES for a given :class:`TrnsysModel` specify initial values,
    such as the initial temperatures of various nodes in a thermal storage tank
    or the initial zone temperatures in a multi zone building.
    """

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to derivatives.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._connected_to = None
        self._parse_types()


class VariableCollection(collections.UserDict):
    """A collection of :class:`VariableType` as a dict. Handles getting and
    setting variable values.
    """

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super(VariableCollection, self).__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """
        Args:
            key:
            value:
        """

        if isinstance(value, TypeVariable):
            """if a TypeVariable is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, (int, float, str)):
            """a str, float, int, etc. is passed"""
            value = _parse_value(
                value, self[key].type, self[key].unit, (self[key].min, self[key].max)
            )
            self[key].__setattr__("value", value)
        elif isinstance(value, _Quantity):
            self[key].__setattr__("value", value.to(self[key].value.units))
        elif isinstance(value, (Equation, Constant)):
            self[key].__setattr__("value", value)
        else:
            raise TypeError(
                "Cannot set a value of type {} in this "
                "VariableCollection".format(type(value))
            )

    @classmethod
    def from_dict(cls, dictionary):
        """
        Args:
            dictionary:
        """
        item = cls()
        for key in dictionary:
            named_key = standerdized_name(dictionary[key].name)
            item.__setitem__(named_key, dictionary[key])
        return item

    @property
    def size(self):
        """The number of parameters"""
        return len(self)


class InitialInputValuesCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Initial Input
    Values
    """

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = "{} Initial Input Values:\n".format(self.size)
        value: TypeVariable
        inputs = "\n".join(
            [
                '"{}": {:~P}'.format(key, value.default)
                for key, value in self.data.items()
            ]
        )
        return num_inputs + inputs

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            type_variable = list(self.values())[key]
        else:
            type_variable = super(VariableCollection, self).__getitem__(key)
        return type_variable

    def __setitem__(self, key, value):
        """Setter for default values (initial values).

        Args:
            key:
            value:
        """

        if isinstance(value, TypeVariable):
            """if a TypeVariable is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, (int, float, str)):
            """a str, float, int, etc. is passed"""
            value = _parse_value(
                value, self[key].type, self[key].unit, (self[key].min, self[key].max)
            )
            self[key].__setattr__("default", value)
        elif isinstance(value, _Quantity):
            self[key].__setattr__("default", value.to(self[key].value.units))
        elif isinstance(value, (Equation, Constant)):
            self[key].__setattr__("default", value)
        else:
            raise TypeError(
                "Cannot set a default value of type {} in this "
                "VariableCollection".format(type(value))
            )

    def _to_deck(self):
        """Returns the string representation for the Initial Input Values"""
        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        head = "*** INITIAL INPUT VALUES\n"
        _ins = [
            (
                v.default.m if isinstance(v.default, _Quantity) else v.default,
                "! {}".format(v.name),
            )
            for v in self.values()
        ]
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")
        return head + core + "\n"


class DerivativesCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Derivatives"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = "{} Inputs:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Returns the string representation for the Input File (.dck)"""

        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        head = "DERIVATIVES {}\n".format(self.size)
        _ins = []
        derivative: TypeVariable
        for derivative in self.values():
            _ins.append((derivative.value.m, "! {}".format(derivative.name)))
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")

        return head + core + "\n"


class InputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Inputs"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = "{} Inputs:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Returns the string representation for the Input File (.dck)"""

        if self.size == 0:
            # Don't need to print empty inputs
            return ""

        head = "INPUTS {}\n".format(self.size)
        # "{u_i}, {o_i}": is an integer number referencing the number of the
        # UNIT to which the ith INPUT is connected. is an integer number
        # indicating to which OUTPUT (i.e., the 1st, 2nd, etc.) of UNIT
        # number ui the ith INPUT is connected.
        _ins = []
        for input in self.values():
            if input.is_connected:
                if isinstance(input.predecessor, TypeVariable):
                    _ins.append(
                        (
                            "{},{}".format(
                                input.predecessor.model.unit_number,
                                input.predecessor.one_based_idx,
                            ),
                            "! {out_model_name}:{output_name} -> {in_model_name}:{"
                            "input_name}".format(
                                out_model_name=input.predecessor.model.name,
                                output_name=input.predecessor.name,
                                in_model_name=input.model.name,
                                input_name=input.name,
                            ),
                        )
                    )
                elif isinstance(input.predecessor, (Equation, Constant)):
                    _ins.append(
                        (
                            input.predecessor.name,
                            "! {out_model_name}:{output_name} -> {in_model_name}:{"
                            "input_name}".format(
                                out_model_name=input.predecessor.model.name,
                                output_name=input.predecessor.name,
                                in_model_name=input.model.name,
                                input_name=input.name,
                            ),
                        )
                    )
                else:
                    raise NotImplementedError(
                        "With unit {}, printing input '{}' connected with output of "
                        "type '{}' from unit '{}' is not supported".format(
                            input.model.name,
                            input.name,
                            type(input.connected_to),
                            input.connected_to.model.name,
                        )
                    )
            else:
                # The input is unconnected.
                _ins.append(
                    (
                        "0,0",
                        "! [unconnected] {in_model_name}:{input_name}".format(
                            in_model_name=input.model.name, input_name=input.name
                        ),
                    )
                )
        core = tabulate.tabulate(_ins, tablefmt="plain", numalign="left")
        return str(head) + core + "\n"


class OutputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Outputs"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = "{} Outputs:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs


class ParameterCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Parameters"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = "{} Parameters:\n".format(self.size)
        inputs = "\n".join(
            ['"{}": {:~P}'.format(key, value.value) for key, value in self.data.items()]
        )
        return num_inputs + inputs

    def _to_deck(self):
        """Returns the string representation for the Input File (.dck)"""

        head = "PARAMETERS {}\n".format(self.size)
        # loop through parameters and print the (value, name) tuples.
        v_ = []
        param: TypeVariable
        for param in self.values():
            if not param._is_question:
                if isinstance(param.value, Equation):
                    v_.append(
                        (
                            param.value.name,
                            "! {} {}".format(param.one_based_idx, param.name),
                        )
                    )
                elif isinstance(param.value, _Quantity):
                    v_.append(
                        (
                            param.value.m,
                            "! {} {}".format(param.one_based_idx, param.name),
                        )
                    )
                else:
                    raise NotImplementedError(
                        "Printing parameter '{}' of type '{}' from unit '{}' is not "
                        "supported".format(
                            param.name, type(param.value), param.model.name
                        )
                    )
        params_str = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return head + params_str + "\n"


class StudioHeader(object):
    """Each TrnsysModel has a StudioHeader which handles the studio comments
    such as position, UNIT_NAME, model, POSITION, LAYER, LINK_STYLE
    """

    def __init__(self, unit_name, model, position, layer=None):
        """
        Args:
            unit_name (str): The unit_name, eg.: "Type104".
            model (Path): The path of the tmf/xml file.
            position (Point, optional): The Point containing coordinates on the
                canvas.
            layer (list, optional): list of layer names on which the model is
                placed. Defaults to "Main".
        """
        if layer is None:
            layer = ["Main"]
        self.layer = layer
        self.position = position
        self.model = model
        self.unit_name = unit_name

    def __str__(self):
        return self._to_deck()

    @classmethod
    def from_component(cls, model):
        """
        Args:
            model (Component):
        """
        position = Point(50, 50)
        layer = ["Main"]
        return cls(model.name, model.model, position, layer)

    def _to_deck(self):
        """
        Examples:
            >>>
            *$UNIT_NAME Boulder, CO
            *$MODEL .\Weather Data Reading and Processing\Standard
            Format\TMY2\Type15-2.tmf
            *$POSITION 69 182
            *$LAYER Main #

        Returns:
            (str): The string representation of the StudioHeader.
        """
        unit_name = "*$UNIT_NAME {}".format(self.unit_name)
        model = "*$MODEL {}".format(self.model)
        position = "*$POSITION {} {}".format(self.position.x, self.position.y)
        layer = "*$LAYER {}".format(" ".join(self.layer))
        return "\n".join([unit_name, model, position, layer]) + "\n"


def _linestyle_to_studio(ls):
    """
    Args:
        ls:
    """
    linestyle_dict = {
        "-": 0,
        "solid": 0,
        "--": 1,
        "dashed": 1,
        ":": 2,
        "dotted": 2,
        "-.": 3,
        "dashdot": 3,
        "-..": 4,
        "dashdotdot": 4,
    }
    _ls = linestyle_dict.get(ls)
    return _ls


def _studio_to_linestyle(ls):
    """
    Args:
        ls:
    """
    linestyle_dict = {0: "-", 1: "--", 2: ":", 3: "-.", 4: "-.."}
    _ls = linestyle_dict.get(ls)
    return _ls


class LinkStyle(object):
    def __init__(
        self,
        u,
        v,
        loc,
        color="black",
        linestyle="-",
        linewidth=None,
        path=None,
        autopath=True,
    ):
        """
        Args:
            u (Component): from Model.
            v (Component): to Model.
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
                ('green'), hex strings ('#008000'), RGB or RGBA tuples
                ((0,1,0,1)) or grayscale intensities as a string ('0.8').
            linestyle (str): Possible values: '-' or 'solid', '--' or 'dashed',
                '-.' or 'dashdot', ':' or 'dotted', '-.' or 'dashdotdot'.
            linewidth (float): The link line width in points.
            path (LineString or MultiLineString): The path the link should
                follow.
        """
        self.u = u
        self.v = v
        self.loc = loc
        self._color = color
        self._linestyle = linestyle
        self._linewidth = linewidth
        self.autopath = autopath
        self._path = None

    @property
    def path(self):
        if self._path is None:
            u_anchor_name, v_anchor_name = self.anchor_ids
            _u = AnchorPoint(self.u).anchor_points[u_anchor_name]
            _v = AnchorPoint(self.v).anchor_points[v_anchor_name]
            if self.autopath:
                self._path = self.u.studio_canvas.shortest_path(_u, _v)
            else:
                line = LineString([_u, _v])
                self._path = redistribute_vertices(line, line.length / 3)
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def anchor_ids(self):
        if isinstance(self.loc, tuple):
            loc_u, loc_v = self.loc
        else:
            loc_u = self.loc
            loc_v = self.loc
        return AnchorPoint(self.u).studio_anchor(self.v, (loc_u, loc_v))

    def __repr__(self):
        return self._to_deck()

    def set_color(self, color):
        """Set the color of the line.

        Args:
            color (color):
        """
        self._color = color

    def get_color(self):
        """Return the line color."""
        return self._color

    def set_linestyle(self, ls):
        """Set the linestyle of the line.

        Args:
            ls (str): Possible values: '-' or 'solid', '--' or 'dashed', '-.' or
                'dashdot', ':' or 'dotted', '-.' or 'dashdotdot'.
        """
        if isinstance(ls, str):
            self._linestyle = ls

    def get_linestyle(self):
        """Return the linestyle.

        See also :meth:`~pyTrnsysType.trnsymodel.LinkStyle.set_linestyle`.
        """
        return self._linestyle

    def set_linewidth(self, lw):
        """Set the line width in points.

        Args:
            lw (float): The line width in points.
        """
        self._linewidth = lw

    def get_linewidth(self):
        """Return the linewidth.

        See also :meth:`~pyTrnsysType.trnsymodel.LinkStyle.set_linewidth`.
        """
        return self._linewidth

    def _to_deck(self):
        """0:20:40:20:1:0:0:0:1:513,441:471,441:471,430:447,430"""
        u_anchor_name, v_anchor_name = self.anchor_ids
        anchors = (
            ":".join(
                [
                    ":".join(
                        map(
                            str,
                            AnchorPoint(self.u).studio_anchor_mapping[u_anchor_name],
                        )
                    ),
                    ":".join(
                        map(
                            str,
                            AnchorPoint(self.u).studio_anchor_mapping[v_anchor_name],
                        )
                    ),
                ]
            )
            + ":"
        )

        color = (
            str(
                get_int_from_rgb(
                    tuple([u * 255 for u in colorConverter.to_rgb(self.get_color())])
                )
            )
            + ":"
        )
        path = ",".join(
            [":".join(map(str, n.astype(int).tolist())) for n in np.array(self.path)]
        )
        linestyle = str(_linestyle_to_studio(self.get_linestyle())) + ":"
        linewidth = str(self.get_linewidth()) + ":"
        connection_set = anchors + "1:" + color + linestyle + linewidth + "1:" + path
        head = "*!LINK {}:{}\n".format(self.u.unit_number, self.v.unit_number)
        tail = "*!CONNECTION_SET {}\n".format(connection_set)
        return head + tail


class AnchorPoint(object):
    """Handles the anchor point. There are 6 anchor points around a component"""

    def __init__(self, model, offset=20, height=40, width=40):
        """
        Args:
            model (Component): The Component.
            offset (float): The offset to give the anchor points from the center
                of the model position.
            height (float): The height of the component in points.
            width (float): The width of the component in points.
        """
        self.offset = offset
        self.model = model
        self.height = height
        self.width = width

    def studio_anchor(self, other, loc):
        """Return the studio anchor based on a location.

        Args:
            other: TrnsysModel
            loc (2-tuple):
        """
        if "best" not in loc:
            return loc
        u_loc, v_loc = loc
        if u_loc == "best":
            u_loc, _ = self.find_best_anchors(other)
        if v_loc == "best":
            _, v_loc = self.find_best_anchors(other)
        return u_loc, v_loc

    def find_best_anchors(self, other):
        """
        Args:
            other:
        """
        dist = {}
        for u in self.anchor_points.values():
            for v in other.anchor_points.values():
                dist[((u.x, u.y), (v.x, v.y))] = u.distance(v)
        (u_coords, v_coords), distance = sorted(dist.items(), key=lambda kv: kv[1])[0]
        u_loc, v_loc = (
            self.reverse_anchor_points[u_coords],
            AnchorPoint(other).reverse_anchor_points[v_coords],
        )
        return u_loc, v_loc

    @property
    def anchor_points(self):
        return self.get_octo_pts_dict(self.offset)

    @property
    def reverse_anchor_points(self):
        pts = self.get_octo_pts_dict(self.offset)
        return {(pt.x, pt.y): key for key, pt in pts.items()}

    @property
    def studio_anchor_mapping(self):
        from shapely.affinity import translate

        p_ = {}
        minx, miny, maxx, maxy = MultiPoint(
            [p for p in self.anchor_points.values()]
        ).bounds
        for k, p in self.anchor_points.items():
            p_[k] = translate(p, -minx, -maxy)
        minx, miny, maxx, maxy = MultiPoint([p for p in p_.values()]).bounds
        for k, p in p_.items():
            p_[k] = translate(p, 0, -miny)
        return {
            k: tuple(itertools.chain(*tuple((map(abs, p) for p in p.coords))))
            for k, p in p_.items()
        }

    @property
    def studio_anchor_reverse_mapping(self):
        return {
            (0, 0): "top-left",
            (20, 0): "top-center",
            (40, 0): "top-right",
            (40, 20): "center-right",
            (40, 40): "bottom-right",
            (20, 40): "bottom-center",
            (0, 40): "bottom-left",
            (0, 20): "center-left",
        }

    def get_octo_pts_dict(self, offset=10):
        """Define 8-anchor :class:`Point` around the :class:`TrnsysModel` in
        cartesian space and return a named-dict with human readable meaning.
        These points are equally dispersed at the four corners and 4 edges of
        the center, at distance = :attr:`offset`

        See :func:`~trnsymodel.TrnsysType.set_link_style` or
        :class:`trnsymodel.LinkStyle` for more details.

        Args:
            offset (float): The offset around the center point of :attr:`self`.

        Note:
            In the Studio, a component has 8 anchor points at the four corners
            and four edges. units.Links can be created on these connections.

            .. image:: ../_static/anchor-pts.png
        """
        from shapely.affinity import translate

        center = self.centroid
        xy_offset = {
            "top-left": (-offset, offset),
            "top-center": (0, offset),
            "top-right": (offset, offset),
            "center-right": (offset, 0),
            "bottom-right": (-offset, -offset),
            "bottom-center": (0, -offset),
            "bottom-left": (-offset, -offset),
            "center-left": (-offset, 0),
        }
        return {key: translate(center, *offset) for key, offset in xy_offset.items()}

    @property
    def centroid(self):
        return self.model.studio.position


class Deck(object):
    """The Deck class holds :class:`TrnsysModel` objects, the
    :class:`ControlCards` and specifies the name of the project. This class
    handles reading from a file (see :func:`read_file`) and printing to a file
    (see :func:`save`).
    """

    def __init__(
        self,
        name,
        author=None,
        date_created=None,
        control_cards=None,
        models=None,
        canvas_width=10000,
        canvas_height=10000,
    ):
        """Initialize a Deck object with parameters:

        Args:
            name (str): The name of the project.
            author (str): The author of the project.
            date_created (str): The creation date. If None, defaults to
                datetime.datetime.now().
            control_cards (ControlCards, optional): The ControlCards. See
                :class:`ControlCards` for more details.
            models (list or ComponentCollection): A list of Components (
                :class:`TrnsysModel`, :class:`EquationCollection`, etc.). If a
                list is passed, it is converted to a :class:`ComponentCollection`.
                name (str): A name for this deck. Could be the name of the project.

        Returns:
            (Deck): The Deck object.
        """
        if not models:
            self.models = ComponentCollection()
        else:
            if isinstance(models, ComponentCollection):
                self.models = models
            elif isinstance(models, list):
                self.models = ComponentCollection(models)
            else:
                raise TypeError(
                    "Cant't create a Deck object with models of "
                    "type '{}'".format(type(models))
                )
            self.models = ComponentCollection(models)
        if control_cards:
            self.control_cards = control_cards
        else:
            self.control_cards = ControlCards.basic_template()
        self.name = name
        self.author = author
        self.date_created = (
            to_datetime(date_created, infer_datetime_format=True).isoformat()
            if date_created
            else datetime.datetime.now().isoformat()
        )

    @classmethod
    def read_file(cls, file, author=None, date_created=None, proforma_root=None):
        """Returns a Deck from a file

        Args:
            file (str): Either the absolute or relative path to the file to be
                opened.
            author (str): The author of the project.
            date_created (str): The creation date. If None, defaults to
                datetime.datetime.now().
            proforma_root (str): Either the absolute or relative path to the
                folder where proformas (in xml format) are stored.
        """
        file = Path(file)
        with open(file) as dcklines:
            dck = cls(
                name=file.basename(),
                author=author,
                date_created=date_created,
                control_cards=None,
            )
            cc = ControlCards()
            dck._control_card = cc
            no_whitelines = list(filter(None, (line.rstrip() for line in dcklines)))
            with tempfile.TemporaryFile("r+") as dcklines:
                dcklines.writelines("\n".join(no_whitelines))
                dcklines.seek(0)
                line = dcklines.readline()
                iteration = 0
                maxiter = 26
                while line:
                    iteration += 1
                    # at each line check for a match with a regex
                    line = cls._parse_logic(cc, dck, dcklines, line, proforma_root)

                    if iteration < maxiter:
                        dcklines.seek(0)
                        line = "\n"

        # assert missing types
        # todo: list types that could not be parsed
        return dck

    def __str__(self):
        return self._to_string()

    @property
    def graph(self):
        import networkx as nx

        G = nx.MultiDiGraph()
        for component in self.models:
            G.add_node(component.unit_number, model=component, pos=component.centroid)
            for output, typevar in component.inputs.items():
                if typevar.is_connected:
                    v = component
                    u = typevar.connected_to.model
                    G.add_edge(
                        u.unit_number,
                        v.unit_number,
                        key=output,
                        from_model=u,
                        to_model=v,
                    )
        return G

    def check_deck_integrity(self):
        """Checks if Deck definition passes a few obvious rules"""

        # Check if external file assignments are all unique.
        from collections import Counter

        ext_files = []
        for model in self.models:
            if isinstance(model, TrnsysModel):
                if model.external_files:
                    for _, file in model.external_files.items():
                        if file:
                            ext_files.append(file.value)
        if sum(1 for i in Counter(ext_files).values() if i > 1):
            lg.warn(
                "Some ExternalFile paths have duplicated names. Please make sure all "
                "ASSIGNED paths are unique unless this is desired."
            )

    def update_models(self, model):
        """Update the Deck.models attribute with a :class:`TrnsysModel` or a
        list of :class:`TrnsysModel`.

        Args:
            model (Component or list of Component):

        Returns:
            None.
        """
        if isinstance(model, Component):
            model = [model]
        for model in model:
            # iterate over models and try to pop the existing one
            if model.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == model.unit_number:
                        self.models.pop(i)
                        break
            # in any case, add new one
            self.models.append(model)

    def remove_models(self, model):
        """
        Args:
            model:
        """
        if isinstance(model, Component):
            model = [model]
        for model in model:
            # iterate over models and try to pop the existing one
            if model.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == model.unit_number:
                        self.models.pop(i)
                        break

    def save(self, filename):
        """Saves the Deck object to file

        Examples:

            >>> from pyTrnsysType import Deck
            >>> deck = Deck()
            >>> deck.save("my_project.dck")

        Args:
            filename (str): The name of the file (with the extension).
        """
        self.check_deck_integrity()

        file = Path(filename)
        dir = file.dirname()
        if dir != "" and not dir.exists():
            file.dirname().makedirs_p()
        with open(file, "w+") as _file:
            deck_str = str(self)
            _file.write(deck_str)

    def _to_string(self):
        end = self.control_cards.__dict__.pop("end", End())
        cc = self.control_cards._to_deck()

        models = "\n\n".join([model._to_deck() for model in self.models])

        model: Component
        styles = "*!LINK_STYLE\n" + "".join(
            map(
                str,
                list(
                    itertools.chain.from_iterable(
                        [model.studio.link_styles.values() for model in self.models]
                    )
                ),
            )
        )

        end = end._to_deck()

        return "\n\n".join([cc, models, end, styles])

    @classmethod
    def _parse_logic(cls, cc, dck, dcklines, line, proforma_root):
        """
        Args:
            cc:
            dck:
            dcklines:
            line:
            proforma_root:
        """
        global component, i
        while line:
            key, match = dck._parse_line(line)
            if key == "end":
                end_ = End()
                cc.set_statement(end_)
            if key == "version":
                version = match.group("version")
                v_ = Version.from_string(version.strip())
                cc.set_statement(v_)
            # identify a ConstantCollection
            if key == "constants":
                n_cnts = match.group(key)
                cb = ConstantCollection()
                for n in range(int(n_cnts)):
                    line = next(iter(dcklines))
                    cb.update(Constant.from_expression(line))
                cc.set_statement(cb)
            if key == "simulation":
                sss = match.group(key).strip()
                start, stop, step = tuple(
                    map(lambda x: dck.return_equation_or_constant(x), sss.split(" "))
                )
                s_ = Simulation(*(start, stop, step))
                cc.set_statement(s_)
            if key == "tolerances":
                sss = match.group(key)
                t_ = Tolerances(*(map(float, map(str.strip, sss.split()))))
                cc.set_statement(t_)
            if key == "limits":
                sss = match.group(key)
                l_ = Limits(*(map(int, map(str.strip, sss.split()))))
                cc.set_statement(l_)
            if key == "dfq":
                k = match.group(key)
                cc.set_statement(DFQ(k.strip()))
            if key == "width":
                w = match.group(key)
                cc.set_statement(Width(w.strip()))
            if key == "list":
                k = match.group(key)
                cc.set_statement(List(*k.strip().split()))
            if key == "solver":
                k = match.group(key)
                cc.set_statement(Solver(*k.strip().split()))
            if key == "nancheck":
                k = match.group(key)
                cc.set_statement(NaNCheck(*k.strip().split()))
            if key == "overwritecheck":
                k = match.group(key)
                cc.set_statement(OverwriteCheck(*k.strip().split()))
            if key == "timereport":
                k = match.group(key)
                cc.set_statement(TimeReport(*k.strip().split()))
            if key == "eqsolver":
                k = match.group(key)
                cc.set_statement(EqSolver(*k.strip().split()))
            if key == "userconstants":
                line = dcklines.readline()
                key, match = dck._parse_line(line)
            # identify an equation block (EquationCollection)
            if key == "equations":
                # extract number of line, number of equations
                n_equations = match.group("equations")
                # read each line of the table until a blank line
                list_eq = []
                for line in [next(iter(dcklines)) for x in range(int(n_equations))]:
                    # extract number and value
                    if line == "\n":
                        continue
                    head, sep, tail = line.strip().partition("!")
                    value = head.strip()
                    # create equation
                    list_eq.append(Equation.from_expression(value))
                component = EquationCollection(list_eq, name=Name("block"))
                dck.remove_models(component)
                component._unit = component.initial_unit_number
                dck.update_models(component)
                # append the dictionary to the data list
            if key == "userconstantend":
                try:
                    dck.update_models(component)
                except NameError:
                    print("Empty UserConstants block")
            # read studio markup
            if key == "unitnumber":
                dck.remove_models(component)
                unit_number = match.group(key)
                component._unit = int(unit_number)
                dck.update_models(component)
            if key == "unitname":
                unit_name = match.group(key)
                component.name = unit_name
            if key == "layer":
                layer = match.group(key)
                component.set_component_layer(layer)
            if key == "position":
                pos = match.group(key)
                component.set_canvas_position(map(float, pos.strip().split()), False)
            # identify a unit (TrnsysModel)
            if key == "unit":
                # extract unit_number, type_number and name
                u = match.group("unitnumber").strip()
                t = match.group("typenumber").strip()
                n = match.group("name").strip()

                xml = Path(proforma_root).glob(f"Type{t}*.xml")
                try:
                    component = TrnsysModel.from_xml(next(iter(xml)), name=n)
                except StopIteration:
                    raise ValueError(f"Could not find proforma for Type{t}")
                else:
                    component._unit = int(u)
                    dck.update_models(component)
            if key == "parameters" or key == "inputs":
                if component._meta.variables:
                    n_vars = int(match.group(key).strip())
                    i = -1
                    while line:
                        i += 1
                        line = dcklines.readline()
                        if not line.strip():
                            line = "\n"
                            i -= 1
                        else:
                            varkey, match = dck._parse_line(line)
                            if varkey == "typevariable":
                                tvar = match.group("typevariable").strip()
                                try:
                                    cls.set_typevariable(dck, i, component, tvar, key)
                                except KeyError:
                                    line = cls._parse_logic(
                                        cc, dck, dcklines, line, proforma_root
                                    )
                            if i == n_vars - 1:
                                line = None
            # identify linkstyles
            if key == "link":
                # identify u,v unit numbers
                u, v = match.group(key).strip().split(":")

                line = dcklines.readline()
                key, match = dck._parse_line(line)

                # identify linkstyle attributes
                if key == "linkstyle":
                    try:
                        _lns = match.groupdict()
                        path = _lns["path"].strip().split(":")

                        mapping = AnchorPoint(
                            dck.models.iloc[int(u)]
                        ).studio_anchor_reverse_mapping

                        def find_closest(mappinglist, coordinate):
                            def distance(a, b):
                                a_ = Point(a)
                                b_ = Point(b)
                                return a_.distance(b_)

                            return min(
                                mappinglist, key=lambda x: distance(x, coordinate)
                            )

                        u_coords = (int(_lns["u1"]), int(_lns["u2"]))
                        v_coords = (int(_lns["v1"]), int(_lns["v2"]))
                        loc = (
                            mapping[find_closest(mapping.keys(), u_coords)],
                            mapping[find_closest(mapping.keys(), v_coords)],
                        )
                        color = get_rgb_from_int(int(_lns["color"]))
                        linestyle = _studio_to_linestyle(int(_lns["linestyle"]))
                        linewidth = int(_lns["linewidth"])

                        path = LineString([list(map(int, p.split(","))) for p in path])

                        dck.models.iloc[int(u)].set_link_style(
                            dck.models.iloc[int(v)],
                            loc,
                            tuple(c / 256 for c in color),
                            linestyle,
                            linewidth,
                            path,
                        )
                    except:
                        pass
            if key == "model":
                _mod = match.group("model")
                tmf = Path(_mod.replace("\\", "/"))
                tmf_basename = tmf.basename()
                try:
                    meta = MetaData.from_xml(tmf)
                except:
                    # replace extension with ".xml" and retry
                    xml_basename = tmf_basename.stripext() + ".xml"
                    proforma_root = Path(proforma_root)
                    if proforma_root is None:
                        proforma_root = Path.getcwd()
                    xmls = proforma_root.glob("*.xml")
                    xml = next((x for x in xmls if x.basename() == xml_basename), None)
                    if not xml:
                        raise ValueError(
                            f"The proforma {xml_basename} could not be found "
                            f"at {proforma_root}"
                        )
                    meta = MetaData.from_xml(xml)
                component.update_meta(meta)

            line = dcklines.readline()
        return line

    def return_equation_or_constant(self, name):
        """
        Args:
            name:
        """
        for n in self.models:
            if name in n.outputs:
                return n[name]
        return Constant(name)

    @staticmethod
    def set_typevariable(dck, i, model, tvar, key):
        """Set the value to the :class:`TypeVariable`.

        Args:
            dck (Deck): the Deck object.
            i (int): the idx of the TypeVariable.
            model (Component): the component to modify.
            tvar (str or float): the new value to set.
            key (str): the specific type of TypeVariable, eg.: 'inputs',
                'parameters', 'outputs'.
        """
        try:
            tvar = float(tvar)
        except:
            # deal with a string, either a Constant or a "[u, n]"
            if "0,0" in tvar:
                # this is an unconnected typevariable, pass.
                pass
            elif "," in tvar:
                unit_number, output_number = map(int, tvar.split(","))
                other = dck.models.iloc[unit_number]
                other.connect_to(model, mapping={output_number - 1: i})
            else:
                if any((tvar in n.outputs) for n in dck.models):
                    # one Equation or Constant has this tvar
                    other = next((n for n in dck.models if (tvar in n.outputs)), None)
                    getattr(model, key)[i] = other[tvar]
                    getattr(model, key)[i]._connected_to = other[tvar]
        else:
            # simply set the new value
            getattr(model, key)[i] = tvar

    def _parse_line(self, line):
        """Do a regex search against all defined regexes and return the key and
        match result of the first matching regex

        Args:
            line (str): the line string to parse.

        Returns:
            2-tuple: the key and the match.
        """

        for key, rx in self._setup_re().items():
            match = rx.search(line)
            if match:
                return key, match
        # if there are no matches
        return None, None

    def _setup_re(self):
        """set up regular expressions. use https://regexper.com to visualise
        these if required
        """

        rx_dict = {
            "version": re.compile(
                r"(?i)(?P<key>^version)(?P<version>.*?)(?=(?:!|\\n|$))"
            ),
            "constants": re.compile(
                r"(?i)(?P<key>^constants)(?P<constants>.*?)(?=(?:!|\\n|$))"
            ),
            "simulation": re.compile(
                r"(?i)(?P<key>^simulation)(" r"?P<simulation>.*?)(?=(?:!|$))"
            ),
            "tolerances": re.compile(
                r"(?i)(?P<key>^tolerances)(" r"?P<tolerances>.*?)(?=(" r"?:!|$))"
            ),
            "limits": re.compile(r"(?i)(?P<key>^limits)(?P<limits>.*?)(?=(" r"?:!|$))"),
            "dfq": re.compile(r"(?i)(?P<key>^dfq)(?P<dfq>.*?)(?=(?:!|$))"),
            "width": re.compile(r"(?i)(?P<key>^width)(?P<width>.*?)(?=(" r"?:!|$))"),
            "list": re.compile(r"(?i)(?P<key>^list)(?P<list>.*?)(?=(" r"?:!|$))"),
            "solver": re.compile(r"(?i)(?P<key>^solver)(?P<solver>.*?)(?=(" r"?:!|$))"),
            "nancheck": re.compile(
                r"(?i)(?P<key>^nan_check)(?P<nancheck>.*?)(?=(" r"?:!|$))"
            ),
            "overwritecheck": re.compile(
                r"(?i)(?P<key>^overwrite_check)(?P<overwritecheck>.*?)(?=(" r"?:!|$))"
            ),
            "timereport": re.compile(
                r"(?i)(?P<key>^time_report)(?P<timereport>.*?)(?=(" r"?:!|$))"
            ),
            "eqsolver": re.compile(
                r"(?i)(?P<key>^eqsolver)(?P<eqsolver>.*?)(?=(" r"?:!|$))"
            ),
            "equations": re.compile(
                r"(?i)(?P<key>^equations)(?P<equations>.*?)(?=(?:!|$))"
            ),
            "userconstantend": re.compile(
                r"(?i)(?P<key>^\*\$user_constants_end)(?P<userconstantend>.*?)("
                r"?=(?:!|$))"
            ),
            "unitnumber": re.compile(
                r"(?i)(?P<key>^\*\$unit_number)(" r"?P<unitnumber>.*?)(?=(?:!|$))"
            ),
            "unitname": re.compile(
                r"(?i)(?P<key>^\*\$unit_name)(?P<unitname>.*?)(?=(?:!|$))"
            ),
            "layer": re.compile(r"(?i)(?P<key>^\*\$layer)(?P<layer>.*?)(?=(?:!|$))"),
            "position": re.compile(
                r"(?i)(?P<key>^\*\$position)(?P<position>.*?)(?=(?:!|$))"
            ),
            "unit": re.compile(
                r"(?i)unit (?P<unitnumber>.*?)type (?P<typenumber>\d*?\s)(?P<name>.*$)"
            ),
            "model": re.compile(
                r"(?i)(?P<key>^\*\$model)(?P<model>.*?)(?=(" r"?:!|$))"
            ),
            "link": re.compile(r"(?i)(^\*!link\s)(?P<link>.*?)(?=(?:!|$))"),
            "linkstyle": re.compile(
                r"(?i)(?:^\*!connection_set )(?P<u1>.*?):(?P<u2>.*?):("
                r"?P<v1>.*?):(?P<v2>.*?):(?P<order>.*?):(?P<color>.*?):("
                r"?P<linestyle>.*?):(?P<linewidth>.*?):(?P<ignored>.*?):("
                r"?P<path>.*?$)"
            ),
            "userconstants": re.compile(
                r"(?i)(?P<key>^\*\$user_constants)(" r"?=(?:!|$))"
            ),
            "parameters": re.compile(
                r"(?i)(?P<key>^parameters )(?P<parameters>.*?)(?=(?:!|$))"
            ),
            "inputs": re.compile(r"(?i)(?P<key>^inputs)(?P<inputs>.*?)(?=(?:!|$))"),
            "typevariable": re.compile(r"^(?![*$!\s])(?P<typevariable>.*?)(?=(?:!|$))"),
            "end": re.compile(r"END"),
        }
        return rx_dict


class ControlCards(object):
    """The :class:`ControlCards` is a container for all the TRNSYS Simulation
    Control Statements and Listing Control Statements. It implements the
    :func:`_to_deck` method which pretty-prints the statements with their
    docstrings.
    """

    def __init__(
        self,
        version=None,
        simulation=None,
        tolerances=None,
        limits=None,
        nancheck=None,
        overwritecheck=None,
        timereport=None,
        dfq=None,
        width=None,
        nocheck=None,
        eqsolver=None,
        solver=None,
        nolist=None,
        list=None,
        map=None,
    ):
        """Each simulation must have SIMULATION and END statements. The other
        simulation control statements are optional. Default values are assumed
        for TOLERANCES, LIMITS, SOLVER, EQSOLVER and DFQ if they are not present

        Args:
            version (Version): The VERSION Statement. labels the deck with the
                TRNSYS version number. See :class:`Version` for more details.
            simulation (Simulation): The SIMULATION Statement.determines the
                starting and stopping times of the simulation as well as the
                time step to be used. See :class:`Simulation` for more details.
            tolerances (Tolerances, optional): Convergence Tolerances (
                TOLERANCES). Specifies the error tolerances to be used during a
                TRNSYS simulation. See :class:`Tolerances` for more details.
            limits (Limits, optional): The LIMITS Statement. Sets limits on the
                number of iterations that will be performed by TRNSYS during a
                time step before it is determined that the differential
                equations and/or algebraic equations are not converging. See
                :class:`Limits` for more details.
            nancheck (NaNCheck, optional): The NAN_CHECK Statement. An optional
                debugging feature in TRNSYS. If the NAN_CHECK statement is
                present, then the TRNSYS kernel checks every output of each
                component at each iteration and generates a clean error if ever
                one of those outputs has been set to the FORTRAN NaN condition.
                See :class:`NaNCheck` for more details.
            overwritecheck (OverwriteCheck, optional): The OVERWRITE_CHECK
                Statement. An optional debugging feature in TRNSYS. Checks to
                make sure that each Type did not write outside its allotted
                space. See :class:`OverwriteCheck` for more details.
            timereport (TimeReport, optional): The TIME_REPORT Statement. Turns
                on or off the internal calculation of the time spent on each
                unit. See :class:`TimeReport` for more details.
            dfq (DFQ, optional): Allows the user to select one of three
                algorithms built into TRNSYS to numerically solve differential
                equations. See :class:`DFQ` for more details.
            width (Width, optional): Set the number of characters to be allowed
                on a line of TRNSYS output. See :class:`Width` for more details.
            nocheck (NoCheck, optional): The Convergence Check Suppression
                Statement. Remove up to 20 inputs for the convergence check. See
                :class:`NoCheck` for more details.
            eqsolver (EqSolver, optional): The Equation Solving Method
                Statement. The order in which blocks of EQUATIONS are solved is
                controlled by the EQSOLVER statement. See :class:`EqSolver` for
                more details.
            solver (Solver, optional): The SOLVER Statement. Select the
                computational scheme. See :class:`Solver` for more details.
            nolist (NoList, optional): The NOLIST Statement. See :class:`NoList`
                for more details.
            list (List, optional): The LIST Statement. See :class:`List` for
                more details.
            map (Map, optional): The MAP Statement. See :class:`Map` for more
                details.

        Note:
            Some Statements have not been implemented because only TRNSYS gods 😇
            use them. Here is a list of Statements that have been ignored:

            - The Convergence Promotion Statement (ACCELERATE)
            - The Calling Order Specification Statement (LOOP)
        """
        super().__init__()
        self.version = version
        self.simulation = simulation

        self.tolerances = tolerances
        self.limits = limits
        self.nancheck = nancheck
        self.overwritecheck = overwritecheck
        self.timereport = timereport

        self.dfq = dfq
        self.nocheck = nocheck
        self.eqsolver = eqsolver
        self.solver = solver

        # Listing Control Statements
        self.nolist = nolist
        self.list = list
        self.map = map

        self.end = End()

    def __repr__(self):
        return self._to_deck()

    @classmethod
    def all(cls):
        """Returns a SimulationCard with all available Statements initialized
        or with their default values. This class method is not recommended since
        many of the Statements are a time consuming process and should be used
        as a debugging tool.
        """
        return cls(
            Version(),
            Simulation(),
            Tolerances(),
            Limits(),
            NaNCheck(n=1),
            OverwriteCheck(n=1),
            TimeReport(n=1),
            DFQ(),
            Width(),
            NoCheck(),
            EqSolver(),
            Solver(),
            NoList(),
            List(activate=True),
            Map(activate=True),
        )

    @classmethod
    def debug_template(cls):
        """Returns a SimulationCard with useful debugging Statements."""
        return cls(
            version=Version(),
            simulation=Simulation(),
            map=Map(activate=True),
            nancheck=NaNCheck(n=1),
            overwritecheck=OverwriteCheck(n=1),
        )

    @classmethod
    def basic_template(cls):
        """Returns a SimulationCard with only the required Statements"""
        return cls(version=Version(), simulation=Simulation())

    def _to_deck(self):
        """Creates a string representation. If the :attr:`doc` is specified, a
        small description is printed in comments
        """
        head = "*** Control Cards\n"
        v_ = []
        for param in self.__dict__.values():
            if isinstance(param, Component):
                v_.append((str(param), None))
            if hasattr(param, "doc"):
                v_.append((str(param), "! {}".format(param.doc)))
            else:
                pass
        statements = tabulate.tabulate(tuple(v_), tablefmt="plain", numalign="left")
        return str(head) + str(statements)

    def set_statement(self, statement):
        """
        Args:
            statement:
        """
        self.__setattr__(statement.__class__.__name__.lower(), statement)


class Name(object):
    """Handles the attribution of user defined names for :class:`TrnsysModel`,
    :class:`EquationCollection` and more.
    """

    existing = []  # a list to store the created names

    def __init__(self, name=None):
        """Pick a name. Will increment the name if already used

        Args:
            name:
        """
        self.name = self.create_unique(name)

    def create_unique(self, name):
        """Check if name has already been used. If so, try to increment until
        not used

        Args:
            name:
        """
        if not name:
            return None
        i = 0
        key = name
        while key in self.existing:
            i += 1
            key = key.split("_")
            key = key[0] + "_{}".format(i)
        the_name = key
        self.existing.append(the_name)
        return the_name

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.name)


class Statement(object):
    """This is the base class for many of the TRNSYS Simulation Control and
    Listing Control Statements. It implements common methods such as the repr()
    method.
    """

    def __init__(self):
        self.doc = ""

    def __repr__(self):
        return self._to_deck()

    def _to_deck(self):
        return ""


class Version(Statement):
    """Added with TRNSYS version 15. The idea of the command is that by labeling
    decks with the TRNSYS version number that they were created under, it is
    easy to keep TRNSYS backwards compatible. The version number is saved by the
    TRNSYS kernel and can be acted upon.
    """

    def __init__(self, v=(18, 0)):
        """Initialize the Version statement

        Args:
            v (tuple): A tuple of (major, minor) eg. 18.0 :> (18, 0)
        """
        super().__init__()
        self.v = v
        self.doc = "The VERSION Statement"

    @classmethod
    def from_string(cls, string):
        """
        Args:
            string:
        """
        return cls(tuple(map(int, string.split("."))))

    def _to_deck(self):
        return "VERSION {}".format(".".join(map(str, self.v)))


class Simulation(Statement):
    """The SIMULATION statement is required for all simulations, and must be
    placed in the TRNSYS input file prior to the first UNIT-TYPE statement. The
    simulation statement determines the starting and stopping times of the
    simulation as well as the time step to be used.
    """

    def __init__(self, start=0, stop=8760, step=1):
        """Initialize the Simulation statement

        Attention:
            With TRNSYS 16 and beyond, the starting time is now specified as the
            time at the beginning of the first time step.

        Args:
            start (int): The hour of the year at which the simulation is to
                begin.
            stop (int): The hour of the year at which the simulation is to end.
            step (float): The time step to be used (hours).
        """
        super().__init__()
        self.start = start
        self.stop = stop
        self.step = step
        self.doc = "Start time\tEnd time\tTime step"

    def _to_deck(self):
        """SIMULATION to tf Δt"""
        return "SIMULATION {} {} {}".format(self.start, self.stop, self.step)


class Tolerances(Statement):
    """The TOLERANCES statement is an optional control statement used to specify
    the error tolerances to be used during a TRNSYS simulation.
    """

    def __init__(self, epsilon_d=0.01, epsilon_a=0.01):
        """
        Args:
            epsilon_d: is a relative (and -epsilon_d is an absolute) error
                tolerance controlling the integration error.
            epsilon_a: is a relative (and -epsilon_a is an absolute) error
                tolerance controlling the convergence of input and output
                variables.
        """
        super().__init__()
        self.epsilon_d = epsilon_d
        self.epsilon_a = epsilon_a
        self.doc = "Integration\tConvergence"

    def _to_deck(self):
        """TOLERANCES 0.001 0.001"""
        head = "TOLERANCES {} {}".format(self.epsilon_d, self.epsilon_a)
        return str(head)


class Limits(Statement):
    """The LIMITS statement is an optional control statement used to set limits
    on the number of iterations that will be performed by TRNSYS during a time
    step before it is determined that the differential equations and/or
    algebraic equations are not converging.
    """

    def __init__(self, m=25, n=10, p=None):
        """
        Args:
            m (int): is the maximum number of iterations which can be performed
                during a time-step before a WARNING message is printed out.
            n (int): is the maximum number of WARNING messages which may be
                printed before the simulation terminates in ERROR.
            p (int, optional): is an optional limit. If any component is called
                p times in one time step, then the component will be traced (See
                Section 2.3.5) for all subsequent calls in the timestep. When p
                is not specified by the user, TRNSYS sets p equal to m.
        """
        super().__init__()
        self.m = m
        self.n = n
        self.p = p if p is not None else self.m
        self.doc = "Max iterations\tMax warnings\tTrace limit"

    def _to_deck(self):
        """TOLERANCES 0.001 0.001"""
        head = "LIMITS {} {} {}".format(self.m, self.n, self.p)
        return str(head)


class NaNCheck(Statement):
    """One problem that has plagued TRNSYS simulation debuggers is that in
    Fortran, the “Not a Number” (NaN) condition can be passed along through
    numerous subroutines without being flagged as an error. For example, a
    division by zero results in a variable being set to NaN. This NaN can then
    be used in subsequent equation, causing them to be set to NaN as well. The
    problem persists for a time until a Range Check or an Integer Overflow error
    occurs and actually stops simulation progress. To alleviate the problem, the
    NAN_CHECK Statement was added as an optional debugging feature in TRNSYS
    input files.
    """

    def __init__(self, n=0):
        """Initialize a NaNCheck object.

        Hint:
            If the NAN_CHECK statement is present (n=1), then the TRNSYS kernel
            checks every output of each component at each iteration and
            generates a clean error if ever one of those outputs has been set to
            the FORTRAN NaN condition. Because this checking is very time
            consuming, users are not advised to leave NAN_CHECK set in their
            input files as it causes simulations to run much more slowly.

        Args:
            n (int): Is 0 if the NAN_CHECK feature is not desired or 1 if
                NAN_CHECK feature is desired. Default is 0.
        """
        super().__init__()
        self.n = int(n)
        self.doc = "The NAN_CHECK Statement"

    def _to_deck(self):
        return "NAN_CHECK {}".format(self.n)


class OverwriteCheck(Statement):
    """A common error in non standard and user written TRNSYS Type routines is
    to reserve too little space in the global output array. By default, each
    Type is accorded 20 spots in the global TRNSYS output array. However, there
    is no way to prevent the Type from then writing in (for example) the 21st
    spot; the entire global output array is always accessible. By activating the
    OVERWRITE_CHECK statement, the TRNSYS kernel checks to make sure that each
    Type did not write outside its allotted space. As with the NAN_CHECK
    statement, OVERWRITE_CHECK is a time consuming process and should only be
    used as a debugging tool when a simulation is ending in error.
    """

    def __init__(self, n=0):
        """Initialize an OVERWRITE_CHECK object.

        Hint:
            OVERWRITE_CHECK is a time consuming process and should only be used
            as a debugging tool when a simulation is ending in error.

        Args:
            n (int): Is 0 if the OVERWRITE_CHECK feature is not desired or 1 if
                OVERWRITE_CHECK feature is desired.
        """
        super().__init__()
        self.n = int(n)
        self.doc = "The OVERWRITE_CHECK Statement"

    def _to_deck(self):
        return "OVERWRITE_CHECK {}".format(self.n)


class TimeReport(Statement):
    """The statement TIME_REPORT turns on or off the internal calculation of the
    time spent on each unit. If this feature is desired, the listing file will
    contain this information at the end of the file.
    """

    def __init__(self, n=0):
        """Initialize a TIME_REPORT object.

        Args:
            n (int): Is 0 if the TIME_REPORT feature is not desired or 1 if
                TIME_REPORT feature is desired.
        """
        super().__init__()
        self.n = n
        self.doc = "The TIME_REPORT Statement"

    def _to_deck(self):
        return "TIME_REPORT {n}".format(n=self.n)


class List(Statement):
    """The LIST statement is used to turn on the TRNSYS processor listing after
    it has been turned off by a NOLIST statement.
    """

    def __init__(self, activate=False):
        """Hint:
            The listing is assumed to be on at the beginning of a TRNSYS input
            file. As many LIST cards as desired may appear in a TRNSYS input
            file and may be located anywhere in the input file.

        Args:
            activate (bool):
        """
        super().__init__()
        self.activate = activate
        self.doc = "The LIST Statement"


class DFQ(Statement):
    """The optional DFQ card allows the user to select one of three algorithms
    built into TRNSYS to numerically solve differential equations (see Manual
    08-Programmer’s Guide for additional information about solution of
    differential equations).
    """

    def __init__(self, k=1):
        """Initialize the Differential Equation Solving Method Statement

        Args:
            k (int, optional): an integer between 1 and 3. If a DFQ card is not
                present in the TRNSYS input file, DFQ 1 is assumed.

        Note:
            The three numerical integration algorithms are:

            1. Modified-Euler method (a 2nd order Runge-Kutta method)
            2. Non-self-starting Heun's method (a 2nd order Predictor-Corrector
               method)
            3. Fourth-order Adams method (a 4th order Predictor-Corrector
               method)
        """
        super().__init__()
        self.k = k
        self.doc = "TRNSYS numerical integration solver method"

    def _to_deck(self):
        return str("DFQ {}".format(self.k))


class Width(Statement):
    """The WIDTH statement is an optional control statement is used to set the
    number of characters to be allowed on a line of TRNSYS output.

    Note:
        This statement is obsolete.
    """

    def __init__(self, n=120):
        """Initialize the Width Statement.

        Args:
            n (int, optional): n is the number of characters per printed line; n
                must be between 72 and 132.
        """
        super().__init__()
        self.k = self._check_range(int(n))
        self.doc = "The number of printed characters per line"

    def _to_deck(self):
        return str("WIDTH {}".format(self.k))

    @staticmethod
    def _check_range(n):
        """
        Args:
            n:
        """
        if n >= 72 and n <= 132:
            return n
        else:
            raise ValueError("The Width Statement mus be between 72 and 132.")


class NoCheck(Statement):
    """TRNSYS allows up to 20 different INPUTS to be removed from the list of
    INPUTS to be checked for convergence (see Section 1.9).
    """

    def __init__(self, inputs=None):
        """
        Args:
            inputs (list of Input):
        """
        super().__init__()
        if not inputs:
            inputs = []
        if len(inputs) > 20:
            raise ValueError(
                "TRNSYS allows only up to 20 different INPUTS to " "be removed"
            )
        self.inputs = inputs
        self.doc = "CHECK Statement"

    def _to_deck(self):
        head = "NOCHECK {}\n".format(len(self.inputs))
        core = "\t".join(
            [
                "{}, {}".format(input.model.unit_number, input.one_based_idx)
                for input in self.inputs
            ]
        )
        return str(head) + str(core)


class NoList(Statement):
    """The NOLIST statement is used to turn off the listing of the TRNSYS input
    file.
    """

    def __init__(self, active=True):
        """
        Args:
            active (bool): Setting activate to True will add the NOLIST statement
        """
        super().__init__()
        self.active = active
        self.doc = "NOLIST statement"

    def _to_deck(self):
        return "NOLIST" if self.active else ""


class Map(Statement):
    """The MAP statement is an optional control statement that is used to obtain
    a component output map listing which is particularly useful in debugging
    component interconnections.
    """

    def __init__(self, activate=True):
        """Setting active to True will add the MAP statement

        Args:
            activate (bool): Setting active to True will add the MAP statement
        """
        super().__init__()
        self.active = activate
        self.doc = "MAP statement"

    def _to_deck(self):
        return "MAP" if self.active else ""


class EqSolver(Statement):
    """With the release of TRNSYS 16, new methods for solving blocks of
    EQUATIONS statements were added. For additional information on EQUATIONS
    statements, please refer to section 6.3.9. The order in which blocks of
    EQUATIONS are solved is controlled by the EQSOLVER statement.
    """

    def __init__(self, n=0):
        """Hint:
            :attr:`n` can have any of the following values:

            1. n=0 (default if no value is provided) if a component output or
               TIME changes, update the block of equations that depend upon
               those values. Then update components that depend upon the first
               block of equations. Continue looping until all equations have
               been updated appropriately. This equation blocking method is most
               like the method used in TRNSYS version 15 and before.
            2. n=1 if a component output or TIME changes by more than the value
               set in the TOLERANCES Statement (see Section 6.3.3), update the
               block of equations that depend upon those values. Then update
               components that depend upon the first block of equations.
               Continue looping until all equations have been updated
               appropriately.
            3. n=2 treat equations as a component and update them only after
               updating all components.

        Args:
            n (int): The order in which the equations are solved.
        """
        super().__init__()
        self.n = n
        self.doc = "EQUATION SOLVER statement"

    def _to_deck(self):
        return "EQSOLVER {}".format(self.n)


class End(Statement):
    """The END statement must be the last line of a TRNSYS input file. It
    signals the TRNSYS processor that no more control statements follow and that
    the simulation may begin.
    """

    def __init__(self):
        super().__init__()
        self.doc = "The END Statement"

    def _to_deck(self):
        return "END"


class Solver(Statement):
    """A SOLVER command has been added to TRNSYS to select the computational
    scheme. The optional SOLVER card allows the user to select one of two
    algorithms built into TRNSYS to numerically solve the system of algebraic
    and differential equations.
    """

    def __init__(self, k=0, rf_min=1, rf_max=1):
        """
        Args:
            k (int): the solution algorithm.
            rf_min (float): the minimum relaxation factor.
            rf_max (float): the maximum relaxation factor.

        Note:
            k is either the integer 0 or 1. If a SOLVER card is not present in
            the TRNSYS input file, SOLVER 0 is assumed. If k = 0, the SOLVER
            statement takes two additional parameters, RFmin and RFmax:

            The two solution algorithms (k) are:
                * 0: Successive Substitution
                * 1: Powell’s Method
        """
        super().__init__()
        self.rf_max = rf_max
        self.rf_min = rf_min
        self.k = k
        self.doc = (
            "Solver statement\tMinimum relaxation factor\tMaximum " "relaxation factor"
        )

    def _to_deck(self):
        return (
            "SOLVER {} {} {}".format(self.k, self.rf_min, self.rf_max)
            if self.k == 0
            else "SOLVER {}".format(self.k)
        )


class Constant(Statement):
    """The CONSTANTS statement is useful when simulating a number of systems
    with identical component configurations but with different parameter values,
    initial input values, or initial values of time dependent variables.
    """

    _new_id = itertools.count(start=1)
    instances = {}

    def __init__(self, name=None, equals_to=None, doc=None):
        """
        Args:
            name (str): The left hand side of the equation.
            equals_to (str, TypeVariable): The right hand side of the equation.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        super().__init__()
        try:
            c_ = Constant.instances[name]
        except:
            self._n = next(self._new_id)
            self.name = name
            self.equals_to = equals_to
            self.doc = doc
        else:
            self._n = c_._n
            self.name = c_.name
            self.equals_to = c_.equals_to
            self.doc = c_.doc
        finally:
            Constant.instances.update({self.name: self})

    @classmethod
    def from_expression(cls, expression, doc=None):
        """Create a Constant from a string expression. Anything before the equal
        sign ("=") will become the Constant's name and anything after will
        become the equality statement.

        Hint:
            The simple expressions are processed much as FORTRAN arithmetic
            statements are, with one significant exceptions. Expressions are
            evaluated from left to right with no precedence accorded to any
            operation over another. This rule must constantly be borne in mind
            when writing long expressions.

        Args:
            expression (str): A user-defined expression to parse.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        if "=" not in expression:
            raise ValueError(
                "The from_expression constructor must contain an expression "
                "with the equal sign"
            )
        a, b = expression.split("=")
        return cls(a.strip(), b.strip(), doc=doc)

    @property
    def constant_number(self):
        """The equation number. Unique"""
        return self._n

    def _to_deck(self):
        return self.equals_to


class ConstantCollection(collections.UserDict, Component):
    """A class that behaves like a dict and that collects one or more
    :class:`Constants`.

    You can pass a dict of Equation or you can pass a list of Equation. In
    the latter, the :attr:`Equation.name` attribute will be used as a key.
    """

    def __init__(self, mutable=None, name=None):
        """Initialize a new ConstantCollection.

        Example:
            >>> c_1 = Constant.from_expression("A = 1")
            >>> c_2 = Constant.from_expression("B = 2")
            >>> ConstantCollection([c_1, c_2])

        Args:
            mutable (Iterable, optional): An iterable.
            name (str): A user defined name for this collection of constants.
                This name will be used to identify this block of constants in
                the .dck file;
        """
        if isinstance(mutable, list):
            _dict = {f.name: f for f in mutable}
        else:
            _dict = mutable
        super().__init__(_dict)
        self.name = Name(name)
        self.studio = StudioHeader.from_component(self)
        self._unit = next(TrnsysModel.initial_unit_number)
        self._connected_to = []

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        value = super().__getitem__(key)
        return value

    def __repr__(self):
        return self._to_deck()

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def update(self, E=None, **F):
        """D.update([E, ]**F). Update D from a dict/list/iterable E and F.
        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for cts.name,
        cts in E: D[cts.name] = cts
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (list, dict or Constant): The constant to add or update in D (
                self).
            F (list, dict or Constant): Other constants to update are passed.
        """
        if isinstance(E, Constant):
            E.model = self
            _e = {E.name: E}
        elif isinstance(E, list):
            _e = {cts.name: cts for cts in E}
        else:
            for v in E.values():
                if not isinstance(v, Constant):
                    raise TypeError(
                        "Can only update an ConstantCollection with a"
                        "Constant, not a {}".format(type(v))
                    )
            _e = {v.name: v for v in E.values()}
        k: Constant
        for k in F:
            if isinstance(F[k], dict):
                _f = {v.name: v for k, v in F.items()}
            elif isinstance(F[k], list):
                _f = {cts.name: cts for cts in F[k]}
            else:
                raise TypeError(
                    "Can only update an ConstantCollection with a"
                    "Constant, not a {}".format(type(F[k]))
                )
            _e.update(_f)
        super(ConstantCollection, self).update(_e)

    @property
    def size(self):
        return len(self)

    @property
    def unit_number(self):
        return self._unit

    def _to_deck(self):
        """To deck representation

        Examples::

            CONSTANTS n
            NAME1 = ... constant 1 ...
            NAME2 = ... constant 2 ...
            •
            •
            •
            NAMEn = ... constant n ...
        """
        header_comment = '* CONSTANTS "{}"\n\n'.format(self.name)
        head = "CONSTANTS {}\n".format(len(self))
        v_ = ((equa.name, "=", str(equa)) for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return str(header_comment) + str(head) + str(core)

    def _get_inputs(self):
        """inputs getter. Sorts by order number each time it is called
        """
        return self

    def _get_outputs(self):
        """outputs getter. Since self is already a  dict, return self.
        """
        return self


class Equation(Statement):
    """The EQUATIONS statement allows variables to be defined as algebraic
    functions of constants, previously defined variables, and outputs from
    TRNSYS components. These variables can then be used in place of numbers in
    the TRNSYS input file to represent inputs to components; numerical values of
    parameters; and initial values of inputs and time-dependent variables. The
    capabilities of the EQUATIONS statement overlap but greatly exceed those of
    the CONSTANTS statement described in the previous section.

    Hint:
        In pyTrnsysType, the Equation class works hand in hand with the
        :class:`EquationCollection` class. This class behaves a little bit like
        the equation component in the TRNSYS Studio, meaning that you can list
        equation in a block, give it a name, etc. See the
        :class:`EquationCollection` class for more details.
    """

    _new_id = itertools.count(start=1)

    def __init__(self, name=None, equals_to=None, doc=None, model=None):
        """
        Args:
            name (str): The left hand side of the equation.
            equals_to (str, TypeVariable): The right hand side of the equation.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        super().__init__()
        self._n = next(self._new_id)
        self.name = name
        self.equals_to = equals_to
        self.doc = doc
        self.model = model  # the TrnsysModel this Equation belongs to.

        self._connected_to = []

    def __repr__(self):
        return " = ".join([self.name, self._to_deck()])

    def __str__(self):
        return self.__repr__()

    @classmethod
    def from_expression(cls, expression, doc=None):
        """Create an equation from a string expression. Anything before the
        equal sign ("=") will become a Constant and anything after will become
        the equality statement.

        Example:
            Create a simple expression like so:

            >>> equa1 = Equation.from_expression("TdbAmb = [011,001]")

        Args:
            expression (str): A user-defined expression to parse.
            doc (str, optional): A small description optionally printed in the
                deck file.
        """
        if "=" not in expression:
            raise ValueError(
                "The from_expression constructor must contain an expression "
                "with the equal sign"
            )
        a, b = expression.split("=")
        return cls(a.strip(), b.strip(), doc=doc)

    @classmethod
    def from_symbolic_expression(cls, name, exp, *args, doc=None):
        """Crate an equation with a combination of a generic expression (with
        placeholder variables) and a list of arguments. The underlying engine
        will use Sympy and symbolic variables. You can use a mixture of
        :class:`TypeVariable` and :class:`Equation`, :class:`Constant` as
        well as the python default :class:`str`.

        .. Important::

            If a `str` is passed in place of an expression argument (
            :attr:`args`), make sure to declare that string as an Equation or
            a Constant later in the routine.

        Examples:
            In this example, we define a variable (var_a) and we want it to be
            equal to the 'Outlet Air Humidity Ratio' divided by 12 + log(
            Temperature to heat source). In a TRNSYS deck file one would have to
            manually determine the unit numbers and output numbers and write
            something like : '[1, 2]/12 + log([1, 1])'. With the
            :func:`~from_symbolic_expression`, we can do this very simply:

            1. first, define the name of the variable:

            >>> name = "var_a"

            2. then, define the expression as a string. Here, the variables `a`
            and `b` are symbols that represent the two type outputs. Note that
            their name has bee chosen arbitrarily.

            >>> exp = "log(a) + b / 12"
            >>> # would be also equivalent to
            >>> exp = "log(x) + y / 12"

            3. here, we define the actual variables (the type outputs) after
            loading our model from its proforma:

            >>> from pyTrnsysType import TrnsysModel
            >>> fan = TrnsysModel.from_xml("fan_type.xml")
            >>> vars = (fan.outputs[0], fan.outputs[1])

            .. Important::

                The order of the symbolic variable encountered in the string
                expression (step 2), from left to right, must be the same for
                the tuple of variables. For instance, `a` is followed by `b`,
                therefore `fan.outputs[0]` is followed by `fan.outputs[1]`.

            4. finally, we create the Equation. Note that vars is passed with
            the '*' declaration to unpack the tuple.

            >>> from pyTrnsysType import Equation
            >>> eq = Equation.from_symbolic_expression(name, exp, *vars)
            >>> print(eq)
            [1, 1]/12 + log([1, 2])

        Args:
            name (str): The name of the variable (left-hand side), of the
                equation.
            exp (str): The expression to evaluate. Use any variable name and
                mathematical expression.
            *args (tuple): A tuple of :class:`TypeVariable` that will replace
                the any variable name specified in the above expression.
            doc (str, optional): A small description optionally printed in the
                deck file.

        Returns:
            Equation: The Equation Statement object.
        """
        from sympy.parsing.sympy_parser import parse_expr

        exp = parse_expr(exp)

        if len(exp.free_symbols) != len(args):
            raise AttributeError(
                "The expression does not have the same number of "
                "variables as arguments passed to the symbolic expression "
                "parser."
            )
        for i, arg in enumerate(sorted(exp.free_symbols, key=lambda sym: sym.name)):
            new_symbol = args[i]
            if isinstance(new_symbol, TypeVariable):
                exp = exp.subs(arg, TypeVariableSymbol(new_symbol))
            elif isinstance(new_symbol, (Equation, Constant)):
                exp = exp.subs(arg, Symbol(new_symbol.name))
            else:
                exp = exp.subs(arg, Symbol(new_symbol))
        return cls(name, exp)

    @property
    def eq_number(self):
        """The equation number. Unique"""
        return self._n

    @property
    def idx(self):
        """The 0-based index of the Equation"""
        ns = {e: i for i, e in enumerate(self.model)}
        return ns[self.name]

    @property
    def one_based_idx(self):
        """The 1-based index of the Equation"""
        return self.idx + 1

    @property
    def unit_number(self):
        return self.model.unit_number

    @property
    def is_connected(self):
        """Whether or not this TypeVariable is connected to another type"""
        return self.connected_to is not None

    @property
    def connected_to(self):
        """The TrnsysModel to which this component is connected"""
        return self._connected_to

    @connected_to.setter
    def connected_to(self, value):
        if isinstance(value, Component):
            # todo: if self._connected_to, restore existing paths from canvas grid
            self._connected_to = value
        else:
            raise TypeError(f"can't set with type{type(value)}")

    def _to_deck(self):
        if isinstance(self.equals_to, TypeVariable):
            return "[{unit_number}, {output_id}]".format(
                unit_number=self.equals_to.model.unit_number,
                output_id=self.equals_to.one_based_idx,
            )
        elif isinstance(self.equals_to, Expr):
            return print_my_latex(self.equals_to)
        else:
            return self.equals_to


class EquationCollection(collections.UserDict, Component):
    """A class that behaves like a dict and that collects one or more
    :class:`Equations`. This class behaves a little bit like the equation
    component in the TRNSYS Studio, meaning that you can list equation in a
    block, give it a name, etc.

    You can pass a dict of Equation or you can pass a list of Equation. In
    this case, the :attr:`Equation.name` attribute will be used as a key.

    Hint:
        Creating equations in PyTrnsysType is done trough the :class:`Equation`
        class. Equations are than collected in this EquationCollection. See the
        :class:`Equation` class for more details.
    """

    def __init__(self, mutable=None, name=None):
        """Initialize a new EquationCollection.

        Example:
            >>> equa1 = Equation.from_expression("TdbAmb = [011,001]")
            >>> equa2 = Equation.from_expression("rhAmb = [011,007]")
            >>> EquationCollection([equa1, equa2])

        Args:
            mutable (Iterable, optional): An iterable (dict or list).
            name (str): A user defined name for this collection of equations.
                This name will be used to identify this block of equations in
                the .dck file;
        """
        if isinstance(mutable, list):
            _dict = {f.name: f for f in mutable}
        else:
            _dict = mutable
        super().__init__(_dict)
        self.name = Name(name)
        self._unit = next(TrnsysModel.initial_unit_number)
        self.studio = StudioHeader.from_component(self)

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        if isinstance(key, int):
            value = list(self.data.values())[key]
        else:
            value = super().__getitem__(key)
        return value

    # def __hash__(self):
    #     return self.unit_number

    def __repr__(self):
        return self._to_deck()

    def __setitem__(self, key, value):
        # optional processing here
        value.model = self
        super().__setitem__(key, value)

    def __hash__(self):
        return self._unit

    def update(self, E=None, **F):
        """D.update([E, ]**F). Update D from a dict/list/iterable E and F.
        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for eq.name,
        eq in E: D[eq.name] = eq
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (list, dict or Equation): The equation to add or update in D (
                self).
            F (list, dict or Equation): Other Equations to update are passed.

        Returns:
            None
        """
        if isinstance(E, Equation):
            E.model = self
            _e = {E.name: E}
        elif isinstance(E, list):
            _e = {eq.name: eq for eq in E}
        else:
            for v in E.values():
                if not isinstance(v, Equation):
                    raise TypeError(
                        "Can only update an EquationCollection with an"
                        "Equation, not a {}".format(type(v))
                    )
            _e = {v.name: v for v in E.values()}
        k: Equation
        for k in F:
            if isinstance(F[k], dict):
                _f = {v.name: v for k, v in F.items()}
            elif isinstance(F[k], list):
                _f = {eq.name: eq for eq in F[k]}
            else:
                raise TypeError(
                    "Can only update an EquationCollection with an"
                    "Equation, not a {}".format(type(F[k]))
                )
            _e.update(_f)
        super(EquationCollection, self).update(_e)

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]

    @property
    def size(self):
        return len(self)

    @property
    def unit_number(self):
        return self._unit

    @property
    def unit_name(self):
        """This type does not have a unit_name. Return component name"""
        return self.name

    @property
    def model(self):
        """This model does not have a proforma. Return class name."""
        return self.__class__.__name__

    def _to_deck(self):
        """To deck representation

        Examples::

            EQUATIONS n
            NAME1 = ... equation 1 ...
            NAME2 = ... equation 2 ...
            •
            •
            •
            NAMEn = ... equation n ...
        """
        header_comment = '* EQUATIONS "{}"\n\n'.format(self.name)
        head = "EQUATIONS {}\n".format(len(self))
        v_ = ((equa.name, "=", equa._to_deck()) for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return str(header_comment) + str(head) + str(core)

    def _get_inputs(self):
        """inputs getter. Sorts by order number each time it is called
        """
        return self

    def _get_outputs(self):
        """outputs getter. Since self is already a  dict, return self.
        """
        return self

    def _get_ordered_filtered_types(self, classe_, store):
        """
        Args:
            classe_:
            store:
        """
        return collections.OrderedDict(
            (attr, self._meta[store][attr])
            for attr in sorted(
                self._get_filtered_types(classe_, store),
                key=lambda key: self._meta[store][key].order,
            )
        )

    def _get_filtered_types(self, classe_, store):
        """
        Args:
            classe_:
            store:
        """
        return filter(
            lambda kv: isinstance(self._meta[store][kv], classe_), self._meta[store]
        )


class Derivatives:
    # Todo: Implement Derivatives
    pass


class Trace:
    # Todo: Implement Trace
    pass


class Format:
    # Todo: Implement Format
    pass
