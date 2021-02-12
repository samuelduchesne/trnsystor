"""Deck module."""

import datetime
import itertools
import logging as lg
import re
import tempfile
from io import StringIO

from pandas import to_datetime
from pandas.io.common import _get_filepath_or_buffer, get_handle
from path import Path
from shapely.geometry import LineString, Point

from trnsystor.anchorpoint import AnchorPoint
from trnsystor.collections.components import ComponentCollection
from trnsystor.collections.constant import ConstantCollection
from trnsystor.collections.equation import EquationCollection
from trnsystor.component import Component
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


class DeckFormatter:
    """Class for handling the formatting of deck files."""

    def __init__(self, obj, path_or_buf, encoding=None, mode="w"):
        """Initialize object."""
        if path_or_buf is None:
            path_or_buf = StringIO()
        io_args = _get_filepath_or_buffer(
            path_or_buf, encoding=encoding, compression=None, mode=mode
        )
        self.path_or_buf = io_args.filepath_or_buffer
        self.obj = obj
        self.mode = mode
        if encoding is None:
            encoding = "utf-8"
        self.encoding = encoding

    def save(self):
        """Create the writer & save."""
        if hasattr(self.path_or_buf, "write"):
            f = self.path_or_buf
            close = False
        else:
            io_handles = get_handle(
                self.path_or_buf,
                self.mode,
                encoding=self.encoding,
                compression=None,
            )
            f = io_handles.handle
            handles = io_handles.created_handles
            close = True
        try:
            deck_str = str(self.obj)
            f.write(deck_str)
        finally:
            if close:
                f.close()
                for _fh in handles:
                    _fh.close()


class Deck(object):
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

        Returns:
            Deck: The Deck object.
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
        """Returns a Deck from a file.

        Args:
            file (str or Path): Either the absolute or relative path to the file to be
                opened.
            author (str): The author of the project.
            date_created (str): The creation date. If None, defaults to
                datetime.datetime.now().
            proforma_root (str): Either the absolute or relative path to the
                folder where proformas (in xml format) are stored.
        """
        file = Path(file)
        with open(file) as dcklines:
            cc = ControlCards()
            dck = cls(
                name=file.basename(),
                author=author,
                date_created=date_created,
                control_cards=cc,
            )
            no_whitelines = list(filter(None, (line.rstrip() for line in dcklines)))
            with tempfile.TemporaryFile("r+") as dcklines:
                dcklines.writelines("\n".join(no_whitelines))
                dcklines.seek(0)
                line = dcklines.readline()
                # parse whole file once
                cls._parse_logic(cc, dck, dcklines, line, proforma_root)

                # parse a second time to complete links
                dcklines.seek(0)
                line = dcklines.readline()
                cls._parse_logic(cc, dck, dcklines, line, proforma_root)

        # assert missing types
        # todo: list types that could not be parsed
        return dck

    def __str__(self):
        """Return deck representation of self."""
        return self._to_string()

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

        ext_files = []
        for model in self.models:
            if isinstance(model, TrnsysModel):
                if model.external_files:
                    for _, file in model.external_files.items():
                        if file:
                            ext_files.append(file.value)
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
        if isinstance(amodel, Component):
            amodel = [amodel]
        for amodel in amodel:
            # iterate over models and try to pop the existing one
            if amodel.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == amodel.unit_number:
                        self.models.pop(i)
                        break
            # in any case, add new one
            self.models.append(amodel)

    def remove_models(self, amodel):
        """Remove `amodel` from self.models."""
        if isinstance(amodel, Component):
            amodel = [amodel]
        for amodel in amodel:
            # iterate over models and try to pop the existing one
            if amodel.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == amodel.unit_number:
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

        return None

    def save(self, path_or_buf, encoding=None, mode="w"):
        """Save Deck to file.

        See :meth:`to_file`
        """
        return self.to_file(path_or_buf, encoding=encoding, mode=mode)

    def _to_string(self):
        end = self.control_cards.__dict__.pop("end", End())
        cc = str(self.control_cards)

        models = "\n\n".join([model._to_deck() for model in self.models])

        model: Component
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
    def _parse_logic(cls, cc, dck, dcklines, line, proforma_root):
        if proforma_root is None:
            proforma_root = Path.getcwd()
        else:
            proforma_root = Path(proforma_root)
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
                start, stop, step, *_ = re.split(r"\s+", match.group(key))
                start, stop, step = tuple(
                    map(
                        lambda x: dck.return_equation_or_constant(x),
                        (start, stop, step),
                    )
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
                        component = TrnsysModel.from_xml(next(iter(xml)), name=n)
                    except StopIteration:
                        raise ValueError(f"Could not find proforma for Type{t}")
                    else:
                        component._unit = int(u)
                        dck.update_models(component)
                else:
                    pass
            if key in ("parameters", "inputs"):
                if component._meta.variables:
                    n_vars = int(match.group(key).strip())
                    init_at = n_vars
                    if key == "inputs":
                        init_at = n_vars
                        n_vars = n_vars * 2
                    i = 0
                    while line:
                        line = dcklines.readline()
                        if not line.strip():
                            line = "\n"
                        else:
                            varkey, match = dck._parse_line(line)
                            if varkey == "typevariable":
                                tvar_group = match.group("typevariable").strip()
                                for j, tvar in enumerate(tvar_group.split(" ")):
                                    try:
                                        if i >= init_at:
                                            key = "initial_input_values"
                                            j = j + i - init_at
                                        else:
                                            j = i
                                        cls.set_typevariable(
                                            dck, j, component, tvar, key
                                        )
                                    except (KeyError, IndexError, ValueError):
                                        continue
                                    finally:
                                        i += 1
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
                    except KeyError:
                        #  "Trying to set a LinkStyle on a non-existent connection.
                        #  Make sure to connect [26]Type2: yFill using '.connect_to()'"
                        pass
            if key == "model":
                _mod = match.group("model").strip()
                tmf = Path(_mod.replace("\\", "/"))
                tmf_basename = tmf.basename()
                try:
                    meta = MetaData.from_xml(tmf)
                except FileNotFoundError:
                    # replace extension with ".xml" and retry
                    xml_basename = tmf_basename.stripext() + ".xml"
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
        """Return Equation or Constant for name.

        If `name` parses to int literal, then the `int` is returned.
        """
        for n in self.models:
            if name in n.outputs:
                return n[name]
        try:
            value = int(name)
        except ValueError:
            return Constant(name)
        else:
            return value

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
                    other = next((n for n in dck.models if (tvar in n.outputs)))
                    other[tvar].connect_to(getattr(model, key)[i])
                except StopIteration:
                    pass
        else:
            # simply set the new value
            getattr(model, key)[i] = tvar

    def _parse_line(self, line):
        """Search against all defined regexes and return (key, match).

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
