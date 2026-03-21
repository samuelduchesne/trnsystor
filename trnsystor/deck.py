"""Deck module."""

import datetime
import itertools
import json
import logging as lg
import os
import re
from io import StringIO
from pathlib import Path

from shapely.geometry import LineString, Point

from trnsystor.anchorpoint import AnchorPoint
from trnsystor.collections.components import ComponentCollection
from trnsystor.collections.constant import ConstantCollection
from trnsystor.collections.equation import EquationCollection
from trnsystor.component import Component
from trnsystor.context import DeckContext, _default_context
from trnsystor.controlcards import ControlCards
from trnsystor.linkstyle import _studio_to_linestyle
from trnsystor.name import Name
from trnsystor.statement import (
    DFQ,
    Constant,
    End,
    EqSolver,
    Equation,
    Limits,
    List,
    NaNCheck,
    OverwriteCheck,
    Simulation,
    Solver,
    TimeReport,
    Tolerances,
    Version,
    Width,
)
from trnsystor.trnsysmodel import MetaData, TrnsysModel
from trnsystor.utils import get_rgb_from_int


def _find_closest(mappinglist, coordinate):
    """Find the closest point in mappinglist to coordinate."""
    return min(
        mappinglist,
        key=lambda x: Point(x).distance(Point(coordinate)),
    )


class DeckFormatter:
    """Class for handling the formatting of deck files."""

    def __init__(self, obj, path_or_buf, encoding=None, mode="w"):
        """Initialize object."""
        if path_or_buf is None:
            path_or_buf = StringIO()
        if encoding is None:
            encoding = "utf-8"
        self.path_or_buf = path_or_buf
        self.obj = obj
        self.mode = mode
        self.encoding = encoding

    def save(self):
        """Create the writer & save."""
        deck_str = str(self.obj)
        if hasattr(self.path_or_buf, "write"):
            self.path_or_buf.write(deck_str)
        else:
            with open(self.path_or_buf, self.mode, encoding=self.encoding) as f:
                f.write(deck_str)


class Deck:
    """Deck class.

    The Deck class holds :class:`TrnsysModel` objects, the
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
        canvas_width=1200,
        canvas_height=1000,
        ctx=None,
    ):
        """Initialize a Deck object.

        Args:
            name (str): The name of the project.
            author (str): The author of the project.
            date_created (str): The creation date. If None, defaults to
                datetime.datetime.now().
            control_cards (ControlCards, optional): The ControlCards. See
                :class:`ControlCards` for more details.
            models (list or trnsystor.collections.components.ComponentCollection):
                A list of Components (:class:`TrnsysModel`,
                :class:`EquationCollection`, etc.). If a list is passed,
                it is converted to a :class:`ComponentCollection`. name (str): A name
                for this deck. Could be the name of the project.
            ctx (DeckContext, optional): Scoped context. Defaults to the
                module-level default context.

        Returns:
            Deck: The Deck object.
        """
        self._ctx = ctx or _default_context
        if not models:
            self.models = ComponentCollection()
        else:
            if isinstance(models, ComponentCollection):
                self.models = models
            elif isinstance(models, list):
                self.models = ComponentCollection(models)
            else:
                raise TypeError(
                    f"Cant't create a Deck object with models of type '{type(models)}'"
                )
            self.models = ComponentCollection(models)
        if control_cards:
            self.control_cards = control_cards
        else:
            self.control_cards = ControlCards.basic_template()
        self.name = name
        self.author = author
        if date_created:
            self.date_created = datetime.datetime.fromisoformat(str(date_created))
        else:
            self.date_created = datetime.datetime.now()

    @classmethod
    def read_file(
        cls, file, author=None, date_created=None, proforma_root=None, **kwargs
    ):
        """Returns a Deck from a file.

        Args:
            file (str or Path): Either the absolute or relative path to the file to be
                opened.
            author (str): The author of the project.
            date_created (str): The creation date. If None, defaults to
                datetime.datetime.now().
            proforma_root (str): Either the absolute or relative path to the
                folder where proformas (in xml format) are stored.
            **kwargs: Keywords passed to the Deck constructor.
        """
        file = Path(file)
        with open(file) as dcklines:
            dck = cls.load(
                dcklines,
                proforma_root,
                name=file.name,
                author=author,
                date_created=date_created,
                **kwargs,
            )

        # assert missing types
        # todo: list types that could not be parsed
        return dck

    def __str__(self):
        """Return deck representation of self."""
        return self._to_string()

    def __repr__(self):
        """Return repr."""
        name = f"{self.name}\n"
        by = (
            f"Created by {self.author} on {self.date_created}.\n"
            if self.author
            else f"Created on {self.date_created:%Y-%m-%d %H:%M}.\n"
        )
        contains = f"Contains {len(self.models)} components."
        return name + by + contains

    @property
    def graph(self):
        """Return the :class:`MultiDiGraph` of self."""
        import networkx as nx

        G = nx.MultiDiGraph()
        for component in self.models:
            G.add_node(component.unit_number, model=component, pos=component.centroid)
            for output, typevar in component.inputs.items():
                if typevar.is_connected:
                    v = component
                    u = typevar.predecessor.model
                    G.add_edge(
                        u.unit_number,
                        v.unit_number,
                        key=output,
                        from_model=u,
                        to_model=v,
                    )
        return G

    def check_deck_integrity(self):
        """Checks if Deck definition passes a few obvious rules."""
        from collections import Counter

        ext_files = [
            file.value
            for model in self.models
            if isinstance(model, TrnsysModel) and model.external_files
            for file in model.external_files.values()
            if file
        ]
        if sum(1 for i in Counter(ext_files).values() if i > 1):
            lg.warning(
                "Some ExternalFile paths have duplicated names. Please make sure all "
                "ASSIGNED paths are unique unless this is desired."
            )

    def update_models(self, amodel):
        """Update the :attr:`models` attribute with a :class:`TrnsysModel` (or list).

        Args:
            amodel (Component or list of Component):

        Returns:
            None.
        """
        models = [amodel] if isinstance(amodel, Component) else amodel
        for model in models:
            # iterate over models and try to pop the existing one
            if model.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == model.unit_number:
                        self.models.pop(i)
                        break
            # in any case, add new one
            self.models.append(model)

    def remove_models(self, amodel):
        """Remove `amodel` from self.models."""
        models = [amodel] if isinstance(amodel, Component) else amodel
        for model in models:
            # iterate over models and try to pop the existing one
            if model.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == model.unit_number:
                        self.models.pop(i)
                        break

    def to_file(self, path_or_buf, encoding=None, mode="w"):
        """Save the Deck object to file.

        Examples:
            >>> from trnsystor.deck import Deck
            >>> deck = Deck("Unnamed")
            >>> deck.to_file("my_project.dck",None,"w")

        Args:
            path_or_buf (Union[str, Path, IO[AnyStr]]): str or file handle, default None
                File path or object, if None is provided the result is returned as
                a string.  If a file object is passed it should be opened with
                `newline=''`, disabling universal newlines.
            encoding (str or None): Encoding to use.
            mode (str): Mode to open path_or_buf with.
        """
        self.check_deck_integrity()

        formatter = DeckFormatter(self, path_or_buf, encoding=encoding, mode=mode)

        formatter.save()

        if path_or_buf is None:
            return formatter.path_or_buf.getvalue()

        return path_or_buf

    def save(self, path_or_buf, encoding=None, mode="w"):
        """Save Deck to file.

        See :meth:`to_file`
        """
        return self.to_file(path_or_buf, encoding=encoding, mode=mode)

    def _to_string(self):
        end = self.control_cards.__dict__.pop("end", End())
        cc = str(self.control_cards)

        models = "\n\n".join([model._to_deck() for model in self.models])

        styles = (
            "\n*!LINK_STYLE\n"
            + "".join(
                map(
                    str,
                    list(
                        itertools.chain.from_iterable(
                            [model.studio.link_styles.values() for model in self.models]
                        )
                    ),
                )
            )
            + "*!LINK_STYLE_END"
        )

        end = end._to_deck()

        return "\n".join([cc, models, end]) + styles

    @classmethod
    def load(cls, fp, proforma_root=None, dck=None, **kwargs):
        """Deserialize fp as a Deck object.

        Args:

            fp (SupportsRead[Union[str, bytes]]): a ``.read()``-supporting file-like
                object containing a Component.
            proforma_root (Union[str, os.PathLike]): The path to a directory of xml
                proformas.
            dck (Deck): Optionally pass a Deck object to act
                upon it. This is used in Deck.read_file.
            **kwargs: Keywords passed to the Deck constructor.

        Returns:
            (Deck): A Deck object containing the parsed TrnsysModel objects.
        """
        return cls.loads(fp.read(), proforma_root=proforma_root, dck=dck, **kwargs)

    @classmethod
    def loads(cls, s, proforma_root=None, dck=None, **kwargs):
        """Deserialize ``s`` to a Python object.

        Args:
            dck:
            s (Union[str, bytes]): a ``str``, ``bytes`` or ``bytearray``
                instance containing a TRNSYS Component.
            proforma_root (Union[str, os.PathLike]): The path to a directory of xml
                proformas.

        Returns:
            (Deck): A Deck object containing the parsed TrnsysModel objects.
        """
        # prep model
        cc = ControlCards()
        if dck is None:
            # Create a fresh context for parsing so that multiple calls to
            # loads/read_file do not share state (unit counters, graphs, etc.).
            # Start the counter high to avoid hash collisions with real unit
            # numbers while components are being created and then reassigned
            # to their deck-specified unit numbers.
            ctx = DeckContext(unit_counter=itertools.count(100_000))
            name = kwargs.pop("name", "unnamed")
            dck = cls(control_cards=cc, name=name, ctx=ctx, **kwargs)

        # decode string of bytes, bytearray
        if isinstance(s, str):
            pass
        else:
            if not isinstance(s, bytes | bytearray):
                raise TypeError(
                    f"the DCK object must be str, bytes or bytearray, "
                    f"not {s.__class__.__name__}"
                )
            s = s.decode(json.detect_encoding(s), "surrogatepass")
        # Remove empty lines from string
        s = os.linesep.join([s.strip() for s in s.splitlines() if s])

        # First pass
        cls._parse_string(cc, dck, proforma_root, s)

        # parse a second time to complete links using previous dck object.
        cls._parse_string(cc, dck, proforma_root, s)
        return dck

    @classmethod
    def _parse_string(cls, cc, dck, proforma_root, s):
        ctx = dck._ctx
        # iterate
        deck_lines = iter(s.splitlines())
        line = next(deck_lines)
        proforma_root = Path.cwd() if proforma_root is None else Path(proforma_root)

        component = None
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
                cb = ConstantCollection(ctx=ctx)
                for _n in range(int(n_cnts)):
                    line = next(deck_lines)
                    cb.update(Constant.from_expression(line, ctx=ctx))
                cc.set_statement(cb)
            if key == "simulation":
                start, stop, step, *_ = re.split(r"\s+", match.group(key))
                start, stop, step = tuple(
                    dck.return_equation_or_constant(x) for x in (start, stop, step)
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
                line = next(deck_lines)
                key, match = dck._parse_line(line)
            # identify an equation block (EquationCollection)
            if key == "equations":
                # extract number of line, number of equations
                n_equations = match.group("equations")
                # read each line of the table until a blank line
                list_eq = []
                for line in [next(deck_lines) for x in range(int(n_equations))]:
                    # extract number and value
                    if line == "\n":
                        continue
                    head, _sep, _tail = line.strip().partition("!")
                    value = head.strip()
                    # create equation
                    list_eq.append(Equation.from_expression(value))
                component = EquationCollection(
                    list_eq, name=Name("block", registry=ctx.names), ctx=ctx
                )
            if key == "userconstantend":
                if component is not None:
                    dck.update_models(component)
                else:
                    print("Empty UserConstants block")
            # read studio markup
            if key == "unitnumber":
                unit_number = match.group(key)
                try:
                    model_ = dck.models.iloc[unit_number]
                except KeyError:
                    pass
                else:
                    dck.models.pop(model_)
                component._set_unit(int(unit_number))
                dck.update_models(component)
            if key == "unitname":
                unit_name = match.group(key).strip()
                component.name = unit_name
            if key == "layer":
                layer = match.group(key).strip()
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
                    component = dck.models.loc[int(u)]
                except KeyError:  # The model has not yet been instantiated
                    try:
                        component = TrnsysModel.from_xml(
                            next(iter(xml)), name=n, ctx=ctx
                        )
                    except StopIteration:
                        # could not find a proforma. Initializing component without
                        # metadata in the hopes that we can parse the xml when key ==
                        # "model" a couple lines further in the file.
                        component = TrnsysModel(None, name=n, ctx=ctx)
                    finally:
                        component._set_unit(int(u))
                        dck.update_models(component)
                else:
                    pass
            if (
                key in ("parameters", "inputs")
                and component._meta is not None
                and component._meta.variables
            ):
                n_vars = int(match.group(key).strip())
                init_at = n_vars
                if key == "inputs":
                    init_at = n_vars
                    n_vars = n_vars * 2
                i = 0
                while line:
                    line = next(deck_lines)
                    if not line.strip():
                        line = "\n"
                    else:
                        varkey, match = dck._parse_line(line)
                        if varkey == "typevariable":
                            tvar_group = match.group("typevariable").strip()
                            for j, tvar in enumerate(tvar_group.split(" ")):
                                i = cls._try_set_typevariable(
                                    dck,
                                    i,
                                    j,
                                    init_at,
                                    key,
                                    component,
                                    tvar,
                                )
                        elif varkey is None:
                            continue
                        if i == n_vars:
                            line = None
            if key == "typevariable":
                # We need to pass because we need to get out of this recursion
                pass
            # identify linkstyles
            if key == "link":
                # identify u,v unit numbers
                u, v = match.group(key).strip().split(":")

                line = next(deck_lines)
                key, match = dck._parse_line(line)

                # identify linkstyle attributes
                if key == "linkstyle":
                    try:
                        _lns = match.groupdict()
                        path = _lns["path"].strip().split(":")

                        mapping = AnchorPoint(
                            dck.models.iloc[int(u)]
                        ).studio_anchor_reverse_mapping

                        u_coords = (int(_lns["u1"]), int(_lns["u2"]))
                        v_coords = (int(_lns["v1"]), int(_lns["v2"]))
                        loc = (
                            mapping[_find_closest(mapping.keys(), u_coords)],
                            mapping[_find_closest(mapping.keys(), v_coords)],
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
                    except KeyError:
                        #  "Trying to set a LinkStyle on a non-existent connection.
                        #  Make sure to connect [26]Type2: yFill using '.connect_to()'"
                        pass
            if key == "model":
                _mod = match.group("model").strip()
                tmf = Path(_mod.replace("\\", "/"))
                try:
                    meta = MetaData.from_xml(tmf)
                except FileNotFoundError as err:
                    # replace extension with ".xml" and retry
                    xml_basename = tmf.stem + ".xml"
                    xmls = proforma_root.glob("*.xml")
                    xml = next((x for x in xmls if x.name == xml_basename), None)
                    if not xml:
                        raise ValueError(
                            f"The proforma {xml_basename} could not be "
                            f"found at '{proforma_root}'\nnor at "
                            f"'{tmf.parent}' as specified in the "
                            f"input string."
                        ) from err
                    meta = MetaData.from_xml(xml)
                if isinstance(component, TrnsysModel):
                    if component._meta is None:
                        component._meta = meta
                    component.update_meta(meta)

            try:
                line = next(deck_lines)
            except StopIteration:
                line = None

    def return_equation_or_constant(self, name):
        """Return Equation or Constant for name.

        If `name` parses to int literal, then the `int` is returned.
        """
        for n in self.models:
            if name in n.outputs:
                return n[name]
        try:
            value = int(name)
        except ValueError:
            return Constant(name, ctx=self._ctx)
        else:
            return value

    @classmethod
    def _try_set_typevariable(cls, dck, i, j, init_at, key, component, tvar):
        """Try to set a typevariable, ignoring parse errors."""
        try:
            tv_key = key
            if i >= init_at:
                tv_key = "initial_input_values"
                j = j + i - init_at
            else:
                j = i
            cls.set_typevariable(dck, j, component, tvar, tv_key)
        except (KeyError, IndexError, ValueError):
            pass
        return i + 1

    @staticmethod
    def set_typevariable(dck, i, model, tvar, key):
        """Set the value to the :class:`TypeVariable`.

        Args:
            dck (Deck): the Deck object.
            i (int): the idx of the TypeVariable.
            model (Component): the component to modify.
            tvar (str or float): the new value to set.
            key (str): the specific type of TypeVariable, eg.: 'inputs',
                'parameters', 'outputs', 'initial_input_values'.
        """
        try:
            tvar = float(tvar)
        except ValueError:  # e.g.: could not convert string to float: '21,1'
            # deal with a string, either a Constant or a "[u, n]"
            if "0,0" in tvar:
                # this is an unconnected typevariable, pass.
                pass
            elif "," in tvar:
                unit_number, output_number = map(int, tvar.split(","))
                other = dck.models.iloc[unit_number]
                other.connect_to(model, mapping={output_number - 1: i})
            else:
                try:
                    # one Equation or Constant has this tvar
                    other = next(n for n in dck.models if (tvar in n.outputs))
                    other[tvar].connect_to(getattr(model, key)[i])
                except StopIteration:
                    pass
        else:
            # simply set the new value
            getattr(model, key)[i] = tvar

    _rx_dict = None

    def _parse_line(self, line):
        """Search against all defined regexes and return (key, match).

        Args:
            line (str): the line string to parse.

        Returns:
            2-tuple: the key and the match.
        """
        if self._rx_dict is None:
            self._rx_dict = self._setup_re()
        for key, rx in self._rx_dict.items():
            match = rx.search(line)
            if match:
                return key, match
        # if there are no matches
        return None, None

    @staticmethod
    def _setup_re():
        """Set up regular expressions.

        Hint:
            Use https://regexper.com to visualise these if required.
        """
        rx_dict = {
            "version": re.compile(
                r"(?i)(?P<key>^version)(?P<version>.*?)(?=(?:!|\\n|$))"
            ),
            "constants": re.compile(
                r"(?i)(?P<key>^constants)(?P<constants>.*?)(?=(?:!|\\n|$))"
            ),
            "simulation": re.compile(
                r"(?i)(?P<key>^simulation)\s*(?P<simulation>.*?)(?=(?:!|$))"
            ),
            "tolerances": re.compile(
                r"(?i)(?P<key>^tolerances)(?P<tolerances>.*?)(?=(?:!|$))"
            ),
            "limits": re.compile(r"(?i)(?P<key>^limits)(?P<limits>.*?)(?=(?:!|$))"),
            "dfq": re.compile(r"(?i)(?P<key>^dfq)(?P<dfq>.*?)(?=(?:!|$))"),
            "width": re.compile(r"(?i)(?P<key>^width)(?P<width>.*?)(?=(?:!|$))"),
            "list": re.compile(r"(?i)(?P<key>^list)(?P<list>.*?)(?=(?:!|$))"),
            "solver": re.compile(r"(?i)(?P<key>^solver)(?P<solver>.*?)(?=(?:!|$))"),
            "nancheck": re.compile(
                r"(?i)(?P<key>^nan_check)(?P<nancheck>.*?)(?=(?:!|$))"
            ),
            "overwritecheck": re.compile(
                r"(?i)(?P<key>^overwrite_check)(?P<overwritecheck>.*?)(?=(?:!|$))"
            ),
            "timereport": re.compile(
                r"(?i)(?P<key>^time_report)(?P<timereport>.*?)(?=(?:!|$))"
            ),
            "eqsolver": re.compile(
                r"(?i)(?P<key>^eqsolver)(?P<eqsolver>.*?)(?=(?:!|$))"
            ),
            "equations": re.compile(
                r"(?i)(?P<key>^equations)(?P<equations>.*?)(?=(?:!|$))"
            ),
            "userconstantend": re.compile(
                r"(?i)(?P<key>^\*\$user_constants_end)(?P<userconstantend>.*?)("
                r"?=(?:!|$))"
            ),
            "unitnumber": re.compile(
                r"(?i)(?P<key>^\*\$unit_number)(?P<unitnumber>.*?)(?=(?:!|$))"
            ),
            "unitname": re.compile(
                r"(?i)(?P<key>^\*\$unit_name)(?P<unitname>.*?)(?=(?:!|$))"
            ),
            "layer": re.compile(r"(?i)(?P<key>^\*\$layer)(?P<layer>.*?)(?=(?:!|$))"),
            "position": re.compile(
                r"(?i)(?P<key>^\*\$position)(?P<position>.*?)(?=(?:!|$))"
            ),
            "unit": re.compile(
                r"(?i)unit\s*(?P<unitnumber>.*?)\s*type\s*(?P<typenumber>\d*?\s)\s*("
                r"?P<name>.*$)"
            ),
            "model": re.compile(r"(?i)(?P<key>^\*\$model)(?P<model>.*?)(?=(?:!|$))"),
            "link": re.compile(r"(?i)(^\*!link\s)(?P<link>.*?)(?=(?:!|$))"),
            "linkstyle": re.compile(
                r"(?i)(?:^\*!connection_set )(?P<u1>.*?):(?P<u2>.*?):("
                r"?P<v1>.*?):(?P<v2>.*?):(?P<order>.*?):(?P<color>.*?):("
                r"?P<linestyle>.*?):(?P<linewidth>.*?):(?P<ignored>.*?):("
                r"?P<path>.*?$)"
            ),
            "userconstants": re.compile(r"(?i)(?P<key>^\*\$user_constants)(?=(?:!|$))"),
            "parameters": re.compile(
                r"(?i)(?P<key>^parameters )(?P<parameters>.*?)(?=(?:!|$))"
            ),
            "inputs": re.compile(r"(?i)(?P<key>^inputs)(?P<inputs>.*?)(?=(?:!|$))"),
            "labels": re.compile(
                r"(?i)(?P<key>^labels )(?P<parameters>.*?)(?=(?:!|$))"
            ),
            "typevariable": re.compile(r"^(?![*$!\s])(?P<typevariable>.*?)(?=(?:!|$))"),
            "end": re.compile(r"END"),
        }
        return rx_dict
