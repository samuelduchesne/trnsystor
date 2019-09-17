import collections
import copy
import itertools
import re
from abc import ABCMeta, abstractmethod

import numpy as np
import tabulate
from bs4 import BeautifulSoup, Tag
from matplotlib.colors import colorConverter
from path import Path
from pint.quantity import _Quantity
from shapely.geometry import Point, LineString, MultiLineString, MultiPoint

import pyTrnsysType
from pyTrnsysType.utils import (
    get_int_from_rgb,
    _parse_value,
    parse_type,
    standerdized_name,
    redistribute_vertices,
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
        **kwargs
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

        self.logical_unit = next(self.logic_unit)

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
                ("ASSIGN", ext_file.value.normcase(), ext_file.logical_unit)
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


class Component(metaclass=ABCMeta):
    new_id = itertools.count(start=1)

    def __init__(self, name, meta):
        """
        Args:
            name:
            meta:
        """
        self._unit = next(TrnsysModel.new_id)
        self.name = name
        self._meta = meta
        self.studio = StudioHeader.from_component(self)

    def __hash__(self):
        return self.unit_number

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.unit_number == other.unit_number
        else:
            return self.unit_number == other

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
            pt = pyTrnsysType.affine_transform(pt)
        self.studio.position = pt

    def change_component_layer(self, layers):
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

        style = LinkStyle(self, other, loc, path=path)

        style.set_color(color)
        style.set_linestyle(linestyle)
        style.set_linewidth(linewidth)
        u = self.unit_number
        v = other.unit_number
        self.studio.link_styles.update({(u, v): style})

    def connect_to(self, other, mapping=None, link_style=None):
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
            other (TrnsysModel): The other object
            mapping (dict): Mapping of inputs to outputs numbers
            link_style (dict, optional):

        Raises:
            TypeError: A `TypeError is raised when trying to connect to anything
                other than a :class:`TrnsysModel` .
        """
        if link_style is None:
            link_style = {}
        if not isinstance(other, TrnsysModel):
            raise TypeError("Only `TrsnsysModel` objects can be connected " "together")
        if mapping is None:
            raise NotImplementedError(
                "Automapping is not yet implemented. " "Please provide a mapping dict"
            )
            # Todo: Implement automapping logic here
        else:
            # loop over the mapping and assign :class:`TypeVariable` to
            # `_connected_to` attribute.
            for from_self, to_other in mapping.items():
                if other.inputs[to_other].is_connected:
                    input = other.inputs[to_other]
                    output = other.inputs[to_other]._connected_to
                    msg = (
                        'The output "{}: {}" of model "{}" is already '
                        'connected to the input "{}: {}" of model '
                        '"{}"'.format(
                            output.idx,
                            output.name,
                            output.model.name,
                            input.idx,
                            input.name,
                            input.model.name,
                        )
                    )
                    raise ValueError(msg)
                else:
                    other.inputs[to_other]._connected_to = self.outputs[from_self]
        self.set_link_style(other, **link_style)


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
        return "Type{}: {}".format(self.type_number, self.name)

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

    def copy(self, invalidate_connections=True):
        """copy object

        Args:
            invalidate_connections (bool): If True, connections to other models
                will be reset.
        """
        new = copy.deepcopy(self)
        new._unit = next(new.new_id)
        if invalidate_connections:
            new.invalidate_connections()
        from shapely.affinity import translate

        pt = translate(self.centroid, 50, 0)
        new.set_canvas_position(pt)
        return new

    def invalidate_connections(self):
        """iterate over inputs/outputs and force :attr:`_connected_to` to
        None
        """
        for key in self.outputs:
            self.outputs[key].__dict__["_connected_to"] = None
        for key in self.inputs:
            self.inputs[key].__dict__["_connected_to"] = None

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

    def _resolve_cycles(self, type_, class_):
        """Cycle resolver. Proformas can contain parameters, inputs and ouputs
        that have a variable number of entries. This will deal with their
        creation each time the linked parameters are changed.

        Args:
            type_:
            class_:
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
        self._connected_to = None
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
        """Whether or not this TypeVariable is connected to another type"""
        return self.connected_to is not None

    @property
    def connected_to(self):
        """The TrnsysModel to which this component is connected"""
        return self._connected_to

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
        **kwargs
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

        self._parse_types()

    def __repr__(self):
        return "{}; units={}; value={:~P}\n{}".format(
            self.name, self.unit, self.value, self.definition
        )


class InitialInputValue(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to Initial Input Values"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to inputs.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

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

        self._parse_types()

    def __repr__(self):
        return "{}; units={}; value={:~P}\n{}".format(
            self.name, self.unit, self.value, self.definition
        )


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
        from pyTrnsysType.input_file import Equation
        from pyTrnsysType.input_file import Constant

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
        from pyTrnsysType.input_file import Equation
        from pyTrnsysType.input_file import Constant

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
        from pyTrnsysType.input_file import Equation
        from pyTrnsysType.input_file import Constant

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
                if isinstance(input.connected_to, TypeVariable):
                    _ins.append(
                        (
                            "{},{}".format(
                                input.connected_to.model.unit_number,
                                input.connected_to.one_based_idx,
                            ),
                            "! {out_model_name}:{output_name} -> {in_model_name}:{input_name}".format(
                                out_model_name=input.connected_to.model.name,
                                output_name=input.connected_to.name,
                                in_model_name=input.model.name,
                                input_name=input.name,
                            ),
                        )
                    )
                elif isinstance(input.connected_to, (Equation, Constant)):
                    _ins.append(
                        (
                            input.connected_to.name,
                            "! {out_model_name}:{output_name} -> {in_model_name}:{input_name}".format(
                                out_model_name=input.connected_to.model.name,
                                output_name=input.connected_to.name,
                                in_model_name=input.model.name,
                                input_name=input.name,
                            ),
                        )
                    )
                else:
                    raise NotImplementedError(
                        "With unit {}, printing input '{}' connected with output of type '{}' from unit '{}' is not supported".format(
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
        from pyTrnsysType.input_file import Equation

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
        self.link_styles = {}
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
        self, u, v, loc, color="black", linestyle="-", linewidth=None, path=None
    ):
        """
        Args:
            u (TrnsysModel): from Model.
            v (TrnsysModel): to Model.
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
        if isinstance(loc, tuple):
            loc_u, loc_v = loc
        else:
            loc_u = loc
            loc_v = loc
        self.v = v
        self.u = u
        self.u_anchor_name, self.v_anchor_name = AnchorPoint(self.u).studio_anchor(
            self.v, (loc_u, loc_v)
        )
        self._color = color
        self._linestyle = linestyle
        self._linewidth = linewidth

        if path is None:
            u = AnchorPoint(self.u).anchor_points[self.u_anchor_name]
            v = AnchorPoint(self.v).anchor_points[self.v_anchor_name]
            line = LineString([u, v])
            self.path = redistribute_vertices(line, line.length / 3)
        else:
            self.path = path

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
        anchors = (
            ":".join(
                [
                    ":".join(
                        map(
                            str,
                            AnchorPoint(self.u).studio_anchor_mapping[
                                self.u_anchor_name
                            ],
                        )
                    ),
                    ":".join(
                        map(
                            str,
                            AnchorPoint(self.u).studio_anchor_mapping[
                                self.v_anchor_name
                            ],
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
            model (TrnsysModel): The TrnsysModel.
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
