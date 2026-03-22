"""Profile trnsystor's main operations using pyinstrument."""

import contextlib
from pathlib import Path

from pyinstrument import Profiler

INPUT_DIR = Path("tests/input_files")
DCK_FILE = INPUT_DIR / "test_deck.dck"
DCK_FILE_2 = INPUT_DIR / "Case600h10.dck"

XML_FILES = sorted(INPUT_DIR.glob("*.xml"))


def profile_xml_parsing():
    from trnsystor.trnsysmodel import TrnsysModel
    for xml in XML_FILES:
        TrnsysModel.from_xml(xml)


def profile_deck_read():
    from trnsystor.deck import Deck
    Deck.read_file(DCK_FILE, proforma_root=str(INPUT_DIR))


def profile_deck_read_case600():
    from trnsystor.deck import Deck
    Deck.read_file(DCK_FILE_2, proforma_root=str(INPUT_DIR))


def profile_roundtrip():
    from trnsystor.deck import Deck
    dck = Deck.read_file(DCK_FILE, proforma_root=str(INPUT_DIR))
    text = str(dck)
    Deck.loads(text, proforma_root=str(INPUT_DIR))


def profile_lexer_parser():
    from trnsystor.parsing.lexer import tokenize
    from trnsystor.parsing.parser import parse
    for dck_path in [DCK_FILE, DCK_FILE_2]:
        if dck_path.exists():
            text = dck_path.read_text()
            for _ in range(20):
                tokenize(text)
                parse(text)


def profile_component_connect():
    from trnsystor.context import DeckContext
    from trnsystor.trnsysmodel import TrnsysModel
    ctx = DeckContext()
    fan = TrnsysModel.from_xml(INPUT_DIR / "Type146.xml", context=ctx)
    tank = TrnsysModel.from_xml(INPUT_DIR / "Type4a.xml", context=ctx)
    with contextlib.suppress(Exception):
        fan.connect_to(tank, mapping={fan.outputs[0]: tank.inputs[0]})


def profile_cycle_expansion():
    from trnsystor.trnsysmodel import TrnsysModel
    pipe = TrnsysModel.from_xml(INPUT_DIR / "Type951.xml")
    with contextlib.suppress(Exception):
        pipe.parameters["Number_of_Fluid_Nodes"].value = 10


SCENARIOS = [
    ("XML Proforma Parsing (all 29 files)", profile_xml_parsing),
    ("Deck Read: test_deck.dck", profile_deck_read),
    ("Deck Read: Case600h10.dck", profile_deck_read_case600),
    ("Round-trip (read -> serialize -> re-parse)", profile_roundtrip),
    ("Lexer + Parser only (20 iterations each)", profile_lexer_parser),
    ("Component Connection", profile_component_connect),
    ("Cycle Parameter Expansion", profile_cycle_expansion),
]


def main():
    print("=" * 78)
    print("trnsystor Performance Profile (pyinstrument) - AFTER optimization")
    print("=" * 78)

    for title, fn in SCENARIOS:
        print(f"\n{'─' * 78}")
        print(f"  {title}")
        print(f"{'─' * 78}")

        profiler = Profiler()
        profiler.start()
        try:
            fn()
        except Exception as e:
            print(f"  [ERROR] {e}")
        profiler.stop()

        print(profiler.output_text(unicode=True, color=False, show_all=False))


if __name__ == "__main__":
    main()
