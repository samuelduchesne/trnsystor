import io
from unittest.mock import patch

from trnsystor.deck import Deck
from trnsystor.component import Component


def test_predecessor_missing_node_handled():
    with patch("builtins.input", return_value="y"):
        deck = Deck.read_file("tests/input_files/test_deck.dck", proforma_root="tests/input_files")
    # remove a model node from the global UNIT_GRAPH
    Component.UNIT_GRAPH.remove_node(deck.models[0])

    # ensure saving the deck does not raise when a model is absent from UNIT_GRAPH
    deck.to_file(io.StringIO(), None, "w")
