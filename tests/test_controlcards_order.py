from trnsystor.controlcards import ControlCards


def test_controlcards_deck_consistency():
    outputs = {ControlCards.basic_template()._to_deck() for _ in range(5)}
    assert len(outputs) == 1
