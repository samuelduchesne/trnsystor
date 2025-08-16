import itertools

import networkx as nx
from path import Path

from trnsystor.component import Component
from trnsystor.deck import Deck


def _parse_deck():
    Component.INIT_UNIT_NUMBER = itertools.count(start=1)
    Component.UNIT_GRAPH = nx.MultiDiGraph()
    return Deck.read_file(
        Path("tests/input_files/test_deck.dck"), proforma_root="tests/input_files"
    )


def test_parse_is_reentrant():
    first = _parse_deck()
    second = _parse_deck()
    assert [type(m).__name__ for m in first.models] == [
        type(m).__name__ for m in second.models
    ]
