# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and pyTrnsysType contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import datetime
import itertools
import logging as lg
import re
import tempfile
from io import StringIO

from pandas import to_datetime
from pandas.io.common import get_filepath_or_buffer, get_handle
from path import Path
from pyTrnsysType.component import Component
from shapely.geometry import Point, LineString

from pyTrnsysType import TrnsysModel, get_rgb_from_int
from pyTrnsysType.anchorpoint import AnchorPoint
from pyTrnsysType.collections.components import ComponentCollection
from pyTrnsysType.collections.constant import ConstantCollection
from pyTrnsysType.collections.equation import EquationCollection
from pyTrnsysType.controlcards import ControlCards
from pyTrnsysType.linkstyle import _studio_to_linestyle
from pyTrnsysType.name import Name
from pyTrnsysType.statement import (
    End,
    Version,
    Constant,
    Simulation,
    Tolerances,
    Limits,
    DFQ,
    Width,
    List,
    Solver,
    NaNCheck,
    OverwriteCheck,
    TimeReport,
    EqSolver,
    Equation,
)
from pyTrnsysType.trnsysmodel import (
    MetaData,
)


class DeckFormatter:
    """Class for handling the formatting of deck files"""

    def __init__(self, obj, path_or_buf, encoding=None, mode="w"):

        if path_or_buf is None:
            path_or_buf = StringIO()
        self.path_or_buf, _, _, _ = get_filepath_or_buffer(
            path_or_buf, encoding=encoding, compression=None, mode=mode
        )
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
            f, handles = get_handle(
                self.path_or_buf,
                self.mode,
                encoding=self.encoding,
                compression=None,
            )
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
            models (list or pyTrnsysType.collections.components.ComponentCollection):
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
            G = nx.compose(G, component.UNIT_GRAPH)
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

    def update_models(self, amodel):
        """Update the Deck.models attribute with a :class:`TrnsysModel` or a
        list of :class:`TrnsysModel`.

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
        """
        Args:
            amodel:
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

    def to_file(self, path_or_buf, encoding=None, mode="w"):
        """Saves the Deck object to file

        Examples:

            >>> from pyTrnsysType.deck import Deck
            >>> deck = Deck("Unnamed")
            >>> deck.to_file("my_project.dck",None,"w")

        Args:
            path_or_buf (Union[str, Path, IO[AnyStr]]): str or file handle, default None
                File path or object, if None is provided the result is returned as
                a string.  If a file object is passed it should be opened with
                `newline=''`, disabling universal newlines.
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
        cc = self.control_cards._to_deck()

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
        """
        Args:
            cc:
            dck:
            dcklines:
            line:
            proforma_root:
        """
        global model, ec, i
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
                ec = EquationCollection(list_eq, name=Name("block"))
                dck.remove_models(ec)
                ec._unit = next(ec.NEW_ID)
                dck.update_models(ec)
                # append the dictionary to the data list
            if key == "userconstantend":
                dck.update_models(ec)
            # read studio markup
            if key == "unitnumber":
                dck.remove_models(ec)
                unit_number = match.group(key)
                ec._unit = int(unit_number)
                dck.update_models(ec)
            if key == "unitname":
                unit_name = match.group(key)
                ec.name = unit_name
            if key == "layer":
                layer = match.group(key)
                ec.set_component_layer(layer)
            if key == "position":
                pos = match.group(key)
                ec.set_canvas_position(map(float, pos.strip().split()), False)
            # identify a unit (TrnsysModel)
            if key == "unit":
                # extract unit_number, type_number and name
                u = match.group("unitnumber").strip()
                t = match.group("typenumber").strip()
                n = match.group("name").strip()

                try:
                    xml = Path("tests/input_files").glob("Type{}*.xml".format(t))
                    model = TrnsysModel.from_xml(next(iter(xml)), name=n)
                except:
                    _meta = MetaData(type=t)
                    model = TrnsysModel(_meta, name=n)
                else:
                    model._unit = int(u)
                    dck.update_models(model)
            if key == "parameters" or key == "inputs":
                if model._meta.variables:
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
                                    cls.set_typevariable(dck, i, model, tvar, key)
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
                        msg = (
                            "The proforma {} could not be found "
                            "at"
                            ' "{}"'.format(xml_basename, proforma_root)
                        )
                        lg.warning(msg)
                        continue
                    meta = MetaData.from_xml(xml)
                model.update_meta(meta)

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
                    other[tvar].connect_to(getattr(model, key)[i])

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
