"""Deck module."""

import datetime
import itertools
import json
import logging as lg
from io import StringIO
from pathlib import Path

from trnsystor.collections.components import ComponentCollection
from trnsystor.component import Component
from trnsystor.context import _default_context
from trnsystor.controlcards import ControlCards
from trnsystor.trnsysmodel import TrnsysModel


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
            models (list or ComponentCollection): A list of Components.
            ctx (DeckContext, optional): Scoped context.
        """
        self._ctx = ctx or _default_context
        if not models:
            self.models = ComponentCollection()
        elif isinstance(models, ComponentCollection):
            self.models = models
        elif isinstance(models, list):
            self.models = ComponentCollection(models)
        else:
            raise TypeError(
                f"Can't create a Deck with models of type '{type(models)}'"
            )
        self.control_cards = control_cards or ControlCards.basic_template()
        self.name = name
        self.author = author
        if date_created:
            self.date_created = datetime.datetime.fromisoformat(
                str(date_created)
            )
        else:
            self.date_created = datetime.datetime.now()

    @classmethod
    def read_file(
        cls, file, author=None, date_created=None, proforma_root=None, **kwargs
    ):
        """Return a Deck from a file.

        Args:
            file (str or Path): Path to the .dck file.
            author (str): The author of the project.
            date_created (str): The creation date.
            proforma_root (str): Path to the folder with XML proformas.
            **kwargs: Keywords passed to the Deck constructor.
        """
        file = Path(file)
        with open(file) as f:
            return cls.loads(
                f.read(),
                proforma_root=proforma_root,
                name=file.name,
                author=author,
                date_created=date_created,
                **kwargs,
            )

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
            G.add_node(
                component.unit_number,
                model=component,
                pos=component.centroid,
            )
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
        """Check if Deck definition passes a few obvious rules."""
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
                "Some ExternalFile paths have duplicated names. Please make "
                "sure all ASSIGNED paths are unique unless this is desired."
            )

    def update_models(self, amodel):
        """Update the :attr:`models` attribute with a Component (or list).

        Args:
            amodel (Component or list of Component):
        """
        models = [amodel] if isinstance(amodel, Component) else amodel
        for model in models:
            if model.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == model.unit_number:
                        self.models.pop(i)
                        break
            self.models.append(model)

    def remove_models(self, amodel):
        """Remove `amodel` from self.models."""
        models = [amodel] if isinstance(amodel, Component) else amodel
        for model in models:
            if model.unit_number in [mod.unit_number for mod in self.models]:
                for i, item in enumerate(self.models):
                    if item.unit_number == model.unit_number:
                        self.models.pop(i)
                        break

    def to_file(self, path_or_buf, encoding=None, mode="w"):
        """Save the Deck object to file.

        Args:
            path_or_buf: str, Path, or file-like object.
            encoding (str or None): Encoding to use.
            mode (str): Mode to open path_or_buf with.
        """
        self.check_deck_integrity()
        deck_str = str(self)
        if path_or_buf is None:
            buf = StringIO()
            buf.write(deck_str)
            return buf.getvalue()
        if hasattr(path_or_buf, "write"):
            path_or_buf.write(deck_str)
        elif isinstance(path_or_buf, str | Path):
            with open(path_or_buf, mode, encoding=encoding or "utf-8") as f:
                f.write(deck_str)
        return path_or_buf

    def save(self, path_or_buf, encoding=None, mode="w"):
        """Save Deck to file. See :meth:`to_file`."""
        return self.to_file(path_or_buf, encoding=encoding, mode=mode)

    def _to_string(self):
        from trnsystor.statement import End

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
                            [
                                model.studio.link_styles.values()
                                for model in self.models
                            ]
                        )
                    ),
                )
            )
            + "*!LINK_STYLE_END"
        )

        end_str = end._to_deck()
        return "\n".join([cc, models, end_str]) + styles

    @classmethod
    def load(cls, fp, proforma_root=None, **kwargs):
        """Deserialize fp as a Deck object.

        Args:
            fp: A ``.read()``-supporting file-like object.
            proforma_root: Path to a directory of xml proformas.
            **kwargs: Keywords passed to the Deck constructor.
        """
        return cls.loads(fp.read(), proforma_root=proforma_root, **kwargs)

    @classmethod
    def loads(cls, s, proforma_root=None, **kwargs):
        """Deserialize ``s`` to a Deck object.

        Uses the new three-stage parsing pipeline: tokenize → parse → resolve.

        Args:
            s (str | bytes | bytearray): A TRNSYS deck file content.
            proforma_root (str | Path | None): Path to XML proformas directory.
            **kwargs: Keywords passed to the Deck constructor.

        Returns:
            Deck: A Deck object with parsed components and connections.
        """
        from trnsystor.parsing.parser import parse
        from trnsystor.parsing.resolver import resolve

        if isinstance(s, bytes | bytearray):
            s = s.decode(json.detect_encoding(s), "surrogatepass")
        elif not isinstance(s, str):
            raise TypeError(
                f"the DCK object must be str, bytes or bytearray, "
                f"not {s.__class__.__name__}"
            )

        parsed = parse(s)
        name = kwargs.pop("name", "unnamed")
        return resolve(
            parsed,
            proforma_root=proforma_root,
            name=name,
            **kwargs,
        )

    def return_equation_or_constant(self, name):
        """Return Equation or Constant for name.

        If `name` parses to int literal, then the `int` is returned.
        """
        from trnsystor.statement import Constant

        for n in self.models:
            if name in n.outputs:
                return n[name]
        try:
            value = int(name)
        except ValueError:
            return Constant(name, ctx=self._ctx)
        else:
            return value

    @staticmethod
    def set_typevariable(dck, i, model, tvar, key):
        """Set the value to a :class:`TypeVariable`.

        Args:
            dck (Deck): the Deck object.
            i (int): the idx of the TypeVariable.
            model (Component): the component to modify.
            tvar (str or float): the new value to set.
            key (str): 'inputs', 'parameters', 'initial_input_values', etc.
        """
        try:
            tvar = float(tvar)
        except ValueError:
            if "0,0" in tvar:
                pass
            elif "," in tvar:
                unit_number, output_number = map(int, tvar.split(","))
                other = dck.models.iloc[unit_number]
                other.connect_to(model, mapping={output_number - 1: i})
            else:
                try:
                    other = next(
                        n for n in dck.models if (tvar in n.outputs)
                    )
                    other[tvar].connect_to(getattr(model, key)[i])
                except StopIteration:
                    pass
        else:
            getattr(model, key)[i] = tvar
