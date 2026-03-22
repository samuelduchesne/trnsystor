"""TrnsysModel module."""

import collections
import copy
import itertools
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from shapely.affinity import translate

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


class MetaData:
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
                3-analytical, 4-experimental and 5-'in assembly' meaning that it
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
        self.modifictionDate = modifictionDate  # has a typo in proforma xml
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

    # Fields that only carry text and don't need live Tag objects.
    _TEXT_FIELDS = frozenset({
        "object", "author", "organization", "editor", "creationDate",
        "modifictionDate", "mode", "validation", "icon", "type",
        "maxInstance", "keywords", "details", "comment", "plugin",
        "variablesComment", "source", "compileCommand",
    })

    @classmethod
    def from_tag(cls, tag, **kwargs):
        """Create a TrnsysModel from an xml tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
            **kwargs:
        """
        # Text-only fields get their text extracted immediately.
        # Structural fields keep a reference (consumed once by _from_tag).
        meta_args: dict = {}
        for child in tag.children:
            if isinstance(child, Tag):
                if child.name in cls._TEXT_FIELDS:
                    meta_args[child.name] = child.text
                else:
                    meta_args[child.name] = child  # reference, no copy
        meta_args.update(kwargs)
        return cls(**{attr: meta_args[attr] for attr in meta_args})

    def check_extra_tags(self, kwargs):
        """Detect extra tags in the proforma and warn.

        Raises:
            UnknownProformaTagError: If unknown tags are present.

        Args:
            kwargs (dict): dictionary of extra keyword-arguments that would be
                passed to the constructor.
        """
        if kwargs:
            import logging

            tag_names = ", ".join(kwargs.keys())
            logging.getLogger(__name__).warning(
                "Unknown tags detected in proforma: %s. "
                "These tags will be ignored. If this causes issues, "
                "please report it at https://github.com/samuelduchesne/trnsystor/issues",
                tag_names,
            )

    def __getitem__(self, item):
        """Get item. self[item]."""
        return getattr(self, item)

    @classmethod
    def from_xml(cls, xml, **kwargs):
        """Initialize MetaData from xml file."""
        xml_file = Path(xml)
        with xml_file.open() as xml_f:
            soup = BeautifulSoup(xml_f, "xml")
            my_objects = soup.find_all("TrnsysModel")
            for trnsystype in my_objects:
                kwargs.pop("name", None)
                meta = cls.from_tag(trnsystype, **kwargs)
                return meta


class TrnsysModel(Component):
    """TrnsysModel class."""

    def __init__(self, meta, name, ctx=None):
        """Initialize object.

        Alone, this __init__ method does not do much. See the :func:`from_xml` class
        method for the official constructor of this class.

        Args:
            meta (MetaData): A class containing the model's metadata.
            name (str): A user-defined name for this model.
            ctx (DeckContext, optional): Scoped context.
        """
        self._cache: dict = {}
        super().__init__(name=name, meta=meta, ctx=ctx)

    def _invalidate_cache(self):
        """Clear cached property values."""
        self._cache.clear()

    def __str__(self):
        """Return repr(self)."""
        return f"[{self.unit_number}]Type{self.type_number}: {self.name}"

    def __repr__(self):
        """Return repr(self)."""
        return f"[{self.unit_number}]Type{self.type_number}: {self.name}"

    @classmethod
    def from_xml(cls, xml, ctx=None, **kwargs):
        """Class method to create a :class:`TrnsysModel` from an xml string.

        Examples:
            Simply pass the xml path to the constructor.

            >>> from trnsystor import TrnsysModel
            >>> fan1 = TrnsysModel.from_xml("tests/input_files/Type146.xml")

        Args:
            xml (str or Path): The path of the xml file.
            ctx (DeckContext, optional): Scoped context.
            **kwargs:

        Returns:
            TrnsysType: The TRNSYS model.
        """
        xml_file = Path(xml)
        with xml_file.open() as xml_f:
            all_types = []
            soup = BeautifulSoup(xml_f, "xml")
            my_objects = soup.find_all("TrnsysModel")
            for trnsystype in my_objects:
                t = cls._from_tag(trnsystype, ctx=ctx, **kwargs)
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
        new._unit = next(new._ctx.unit_counter)
        new._ctx.graph.add_node(new)
        if invalidate_connections:
            new.invalidate_connections()

        pt = translate(self.centroid, 50, 0)
        new.set_canvas_position(pt)
        return new

    @property
    def derivatives(self) -> DerivativesCollection:
        """Return derivatives of self."""
        if "derivatives" not in self._cache:
            self._cache["derivatives"] = self._get_derivatives()
        return self._cache["derivatives"]

    @property
    def special_cards(self) -> SpecialCardsCollection:
        """Return special cards of self."""
        if "special_cards" not in self._cache:
            self._cache["special_cards"] = self._get_special_cards()
        return self._cache["special_cards"]

    @property
    def initial_input_values(self) -> InitialInputValuesCollection:
        """Return initial input values of self."""
        if "initial_input_values" not in self._cache:
            self._cache["initial_input_values"] = self._get_initial_input_values()
        return self._cache["initial_input_values"]

    @property
    def parameters(self) -> ParameterCollection:
        """Return parameters of self."""
        if "parameters" not in self._cache:
            self._cache["parameters"] = self._get_parameters()
        return self._cache["parameters"]

    @property
    def external_files(self) -> ExternalFileCollection:
        """Return external files of self."""
        if "external_files" not in self._cache:
            self._cache["external_files"] = self._get_external_files()
        return self._cache["external_files"]

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
    def _from_tag(cls, tag, ctx=None, **kwargs):
        """Class method to create a :class:`TrnsysModel` from a tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
            ctx (DeckContext, optional): Scoped context.
            **kwargs:

        Returns:
            TrnsysModel: The TRNSYS model.
        """
        name = kwargs.pop("name", tag.find("object").text).strip()
        meta = MetaData.from_tag(tag, **kwargs)

        model = cls(meta, name, ctx=ctx)
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
                ExternalFile.from_tag(tag, file_counter=model._ctx.file_counter)
                for tag in tag.find("externalFiles").children
                if isinstance(tag, Tag)
            ]
            if tag.find("externalFiles")
            else None
        )
        model._meta.external_files = (
            {id(var): var for var in file_vars} if file_vars else None
        )

        # Eagerly populate cache
        model._cache["inputs"] = model._get_inputs()
        model._cache["outputs"] = model._get_outputs()
        model._cache["parameters"] = model._get_parameters()
        model._cache["external_files"] = model._get_external_files()

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
            special_cards_list = [
                self._meta["special_cards"][attr]
                for attr in self._get_filtered_types(SpecialCard, "special_cards")
            ]
            return SpecialCardsCollection(special_cards_list)
        else:
            return SpecialCardsCollection()  # return empty collection

    def _get_external_files(self):
        if self._meta.external_files:
            ext_files_dict = {
                attr: self._meta["external_files"][attr]
                for attr in self._get_filtered_types(ExternalFile, "external_files")
            }
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
        for cycle in cycles.values():
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
                for sub_cycle in cycle.cycles:
                    existing = next(
                        (
                            key
                            for key, value in output_dict.items()
                            if value.name == sub_cycle.question
                        ),
                        None,
                    )
                    if not existing:
                        name = sub_cycle.question
                        question_var: TypeVariable = class_(
                            val=sub_cycle.default,
                            name=name,
                            role=sub_cycle.role,
                            unit="-",
                            type=int,
                            dimension="any",
                            min=int(sub_cycle.minSize),
                            max=int(sub_cycle.maxSize),
                            order=9999999,
                            default=sub_cycle.default,
                            model=self,
                        )
                        question_var._is_question = True
                        self._meta.variables.update({id(question_var): question_var})
                        output_dict.update({id(question_var): question_var})
                        from trnsystor.quantity import Quantity as _Qty

                        qv = question_var.value
                        n_times.append(qv.m if isinstance(qv, _Qty) else int(float(str(qv))))
                    else:
                        ev = output_dict[existing].value
                        from trnsystor.quantity import Quantity as _Qty

                        n_times.append(ev.m if isinstance(ev, _Qty) else int(float(str(ev))))
            else:
                from trnsystor.quantity import Quantity as _Qty

                def _get_m(v):
                    return v.m if isinstance(v, _Qty) else int(float(str(v)))

                n_times = [
                    _get_m(
                        next(
                            filter(
                                lambda elem: elem[1].name == cycle.paramName,
                                self._meta.variables.items(),
                            )
                        )[1].value
                    )
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
            for item_or_none, n_time in items_list:
                assert item_or_none is not None
                item = item_or_none
                item._iscyclebase = True
                basename = str(item.name)
                item_base = self._meta.variables.get(id(item))
                for n, _ in enumerate(range(int(n_time)), start=1):
                    existing = next(
                        (
                            key
                            for key, value in mydict.items()
                            if value.name == basename + f"-{n}"
                        ),
                        None,
                    )
                    if existing is not None:
                        item = mydict.get(existing, item_base.copy())
                    else:
                        item = item_base.copy() if item_base else item
                    assert item is not None
                    item._iscyclebase = False  # return it back to False
                    if item._iscycle:
                        self._meta.variables.update({id(item): item})
                    else:
                        item.name = str(basename) + f"-{n}"
                        if item.order is not None:
                            item.order += 1 if n_time > 1 else 0
                        item._iscycle = True
                        self._meta.variables.update({id(item): item})

    def _to_deck(self):
        """Return deck representation of self."""
        from trnsystor.serialization.components import serialize_trnsys_model

        return serialize_trnsys_model(self)

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
                        ExternalFile.from_tag(tag, file_counter=self._ctx.file_counter)
                        for tag in tag
                        if isinstance(tag, Tag)
                    }
                }
            )

    def plot(self, show=True):
        """Plot the model.

        Args:
            show (bool): If True (default), display the plot interactively.
                Set to False in tests or non-interactive environments.
        """
        assert self._meta is not None, "plot() requires a fully-initialized model"
        import matplotlib.pyplot as plt
        import networkx as nx

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
        if show:
            plt.show()
        return ax
