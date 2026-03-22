"""DeckContext module - scoped mutable state for a deck's lifecycle.

Instead of relying on class-level globals (Component.UNIT_GRAPH, etc.),
each Deck or standalone session owns a DeckContext that holds the
connection graph, unit counter, canvas, and name/constant registries.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from trnsystor.canvas import StudioCanvas

if TYPE_CHECKING:
    from collections.abc import Iterator

    from trnsystor.statement.constant import Constant


def _make_graph():
    """Create a new MultiDiGraph, lazily importing networkx."""
    import networkx as nx

    return nx.MultiDiGraph()


@dataclass
class DeckContext:
    """Scoped mutable state for a single deck's lifecycle."""

    graph: object = field(default_factory=_make_graph)
    unit_counter: Iterator[int] = field(default_factory=lambda: itertools.count(1))
    canvas: StudioCanvas = field(default_factory=StudioCanvas)
    names: set[str] = field(default_factory=set)
    constants: dict[str, Constant] = field(default_factory=dict)
    file_counter: Iterator[int] = field(default_factory=lambda: itertools.count(30))

    def __deepcopy__(self, memo):
        """Return self on deepcopy - context is shared, not copied."""
        return self


_default_context = DeckContext()
