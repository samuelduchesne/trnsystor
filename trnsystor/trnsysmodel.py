"""TrnsysModel module."""
import collections
import copy
import itertools

import networkx as nx
from bs4 import BeautifulSoup, Tag
from path import Path

from trnsystor.anchorpoint import AnchorPoint
from trnsystor.collections.cycle import CycleCollection
from trnsystor.collections.derivatives import DerivativesCollection
from trnsystor.collections.externalfile import ExternalFileCollection
from trnsystor.collections.initialinputvalues import InitialInputValuesCollection
from trnsystor.collections.input import InputCollection
from trnsystor.collections.output import OutputCollection
from trnsystor.collections.parameter import ParameterCollection
from trnsystor.collections.specialcards import SpecialCardsCollection
from trnsystor.component import Component
from trnsystor.externalfile import ExternalFile
from trnsystor.specialcard import SpecialCard
from trnsystor.studio import StudioHeader
from trnsystor.typecycle import TypeCycle
from trnsystor.typevariable import Derivative, Input, Output, Parameter, TypeVariable


class MetaData(object):
    """General information that is associated with a :class:`TrnsysModel`."""

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
        specialCards=None,
        **kwargs,
    ):
        """Initialize object with arguments.

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
            externalFiles (trnsystor.external_file.ExternalFileCollection): A
                class handling ExternalFiles for this object.
            compileCommand (str): Command used to recompile this type.
            model (Path): Path of the xml or tmf file.
            specialCards (list of SpecialCards): List of SpecialCards.
            **kwargs: Other keyword arguments passed to the constructor.
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
        self.special_cards = specialCards

        self.check_extra_tags(kwargs)

    @classmethod
    def from_tag(cls, tag, **kwargs):
        """Create a TrnsysModel from an xml tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
            **kwargs:
        """
        meta_args = {
            child.name: child.__copy__()
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
        """Get item. self[item]."""
        return getattr(self, item)

    @classmethod
    def from_xml(cls, xml, **kwargs):
        """Initialize MetaData from xml file."""
        xml_file = Path(xml)
        with open(xml_file) as xml:
            soup = BeautifulSoup(xml, "xml")
            my_objects = soup.findAll("TrnsysModel")
            for trnsystype in my_objects:
                kwargs.pop("name", None)
                meta = cls.from_tag(trnsystype, **kwargs)
                return meta


class TrnsysModel(Component):
    """TrnsysModel class."""

    def __init__(self, meta, name):
        """Initialize object.

        Alone, this __init__ method does not do much. See the :func:`from_xml` class
        method for the official constructor of this class.

        Args:
            meta (MetaData): A class containing the model's metadata.
            name (str): A user-defined name for this model.
        """
        super().__init__(name=name, meta=meta)

    def __str__(self):
        """Return repr(self)."""
        return f"[{self.unit_number}]Type{self.type_number}: {self.name}"

    def __repr__(self):
        """Return repr(self)."""
        return f"[{self.unit_number}]Type{self.type_number}: {self.name}"

    @classmethod
    def from_xml(cls, xml, **kwargs):
        """Class method to create a :class:`TrnsysModel` from an xml string.

        Examples:
            Simply pass the xml path to the constructor.

            >>> from trnsystor import TrnsysModel
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
        """Copy object.

        The new object has a new unit_number.
        The new object is translated by 50 pts to the right on the canvas.

        Args:
            invalidate_connections (bool): If True, connections to other models
                will be reset.
        """
        new = copy.deepcopy(self)
        new._unit = next(new.INIT_UNIT_NUMBER)
        new.UNIT_GRAPH.add_node(new)
        if invalidate_connections:
            new.invalidate_connections()
        from shapely.affinity import translate

        pt = translate(self.centroid, 50, 0)
        new.set_canvas_position(pt)
        return new

    @property
    def derivatives(self) -> DerivativesCollection:
        """Return derivatives of self."""
        return self._get_derivatives()

    @property
    def special_cards(self) -> SpecialCardsCollection:
        """Return special cards of self."""
        return self._get_special_cards()

    @property
    def initial_input_values(self) -> InitialInputValuesCollection:
        """Return initial input values of self."""
        return self._get_initial_input_values()

    @property
    def parameters(self) -> ParameterCollection:
        """Return parameters of self."""
        return self._get_parameters()

    @property
    def external_files(self) -> ExternalFileCollection:
        """Return external files of self."""
        return self._get_external_files()

    @property
    def anchor_points(self) -> dict:
        """Return the 8-AnchorPoints as a dict.

        The anchor point location ('top-left', etc.) is the key.
        """
        return AnchorPoint(self).anchor_points

    @property
    def reverse_anchor_points(self):
        """Reverse anchor points."""
        return AnchorPoint(self).reverse_anchor_points

    @classmethod
    def _from_tag(cls, tag, **kwargs):
        """Class method to create a :class:`TrnsysModel` from a tag.

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
        special_cards = (
            [
                SpecialCard.from_tag(tag)
                for tag in tag.find("specialCards").children
                if isinstance(tag, Tag)
            ]
            if tag.find("specialCards")
            else None
        )
        model._meta.variables = {id(var): var for var in type_vars}
        model._meta.cycles = type_cycles
        model._meta.special_cards = (
            {id(var): var for var in special_cards} if special_cards else None
        )
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
        """Get initial input values."""
        try:
            self._resolve_cycles("input", Input)
            input_dict = self._get_ordered_filtered_types(Input, "variables")
            # filter out cyclebases
            input_dict = {
                k: v for k, v in input_dict.items() if v._iscyclebase is False
            }
            return InitialInputValuesCollection.from_dict(input_dict)
        except TypeError:
            return InitialInputValuesCollection()

    def _get_inputs(self):
        """Get inputs.

        Sorts by order number and resolves cycles each time it is called.
        """
        try:
            self._resolve_cycles("input", Input)
            input_dict = self._get_ordered_filtered_types(Input, "variables")
            # filter out cyclebases
            input_dict = {
                k: v for k, v in input_dict.items() if v._iscyclebase is False
            }
            return InputCollection.from_dict(input_dict)
        except TypeError:
            return InputCollection()

    def _get_outputs(self):
        """Sorts by order number and resolves cycles each time it is called."""
        # output_dict = self._get_ordered_filtered_types(Output)
        try:
            self._resolve_cycles("output", Output)
            output_dict = self._get_ordered_filtered_types(Output, "variables")
            # filter out cyclebases
            output_dict = {
                k: v for k, v in output_dict.items() if v._iscyclebase is False
            }
            return OutputCollection.from_dict(output_dict)
        except TypeError:
            return OutputCollection()

    def _get_parameters(self):
        """Sorts by order number and resolves cycles each time it is called."""
        self._resolve_cycles("parameter", Parameter)
        param_dict = self._get_ordered_filtered_types(Parameter, "variables")
        # filter out cyclebases
        param_dict = {k: v for k, v in param_dict.items() if v._iscyclebase is False}
        return ParameterCollection.from_dict(param_dict)

    def _get_derivatives(self):
        self._resolve_cycles("derivative", Derivative)
        deriv_dict = self._get_ordered_filtered_types(Derivative, "variables")
        # filter out cyclebases
        deriv_dict = {k: v for k, v in deriv_dict.items() if v._iscyclebase is False}
        return DerivativesCollection.from_dict(deriv_dict)

    def _get_special_cards(self):
        if self._meta.special_cards:
            special_cards_list = list(
                self._meta["special_cards"][attr]
                for attr in self._get_filtered_types(SpecialCard, "special_cards")
            )
            return SpecialCardsCollection(special_cards_list)
        else:
            return SpecialCardsCollection()  # return empty collection

    def _get_external_files(self):
        if self._meta.external_files:
            ext_files_dict = dict(
                (attr, self._meta["external_files"][attr])
                for attr in self._get_filtered_types(ExternalFile, "external_files")
            )
            return ExternalFileCollection.from_dict(ext_files_dict)
        else:
            return ExternalFileCollection()  # return empty collection

    def _get_ordered_filtered_types(self, class_name, store):
        """Return an ordered dict of :class:`TypeVariable`.

        Filtered by *class_name* and ordered by their order number attribute.

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
        """Return a filter of TypeVariables from the self._meta[store] by *class_name*.

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
        """Cycle resolver.

        Proformas can contain parameters, inputs and outputs that have a variable
        number of entries. This will deal with their creation each time the linked
        parameters are changed.
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
        """Return deck representation of self."""
        unit_type = f"UNIT {self.unit_number} TYPE  {self.type_number} {self.name}\n"
        studio = self.studio
        params = self.parameters
        inputs = self.inputs
        initial_input_values = self.initial_input_values
        special_cards = self.special_cards
        derivatives = self.derivatives
        externals = self.external_files

        return (
            str(unit_type)
            + str(studio)
            + str(params)
            + str(inputs)
            + str(initial_input_values)
            + str(special_cards)
            + str(derivatives)
            + str(externals)
        )

    def update_meta(self, new_meta):
        """Update self with new :class:`MetaData`."""
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
        tag = new_meta.special_cards or {}
        special_cards = [
            SpecialCard.from_tag(tag) for tag in tag if isinstance(tag, Tag)
        ]
        self._meta.variables = {id(var): var for var in type_vars}
        self._meta.cycles = type_cycles
        self._meta.special_cards = {id(var): var for var in special_cards}

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

    def plot(self):
        """Plot the model."""
        import matplotlib.pyplot as plt

        G = nx.DiGraph()
        G.add_edges_from(("type", output.name) for output in self.outputs.values())
        G.add_edges_from((input.name, "type") for input in self.inputs.values())
        pos = nx.drawing.planar_layout(G, center=(50, 50))
        ax = nx.draw_networkx(
            G,
            pos,
            with_labels=True,
            arrows=True,
            width=4,
        )
        nx.draw_networkx_edge_labels(
            G,
            pos,
            edge_labels={
                ("type", output.name): output.name for output in self.outputs.values()
            },
            ax=ax,
        )
        plt.show()
        return ax
