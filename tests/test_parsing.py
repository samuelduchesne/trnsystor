"""Tests for the new parsing infrastructure (lexer + parser)."""

from pathlib import Path

from trnsystor.parsing.lexer import TokenKind, tokenize
from trnsystor.parsing.parser import parse


DCK_FILE = Path("tests/input_files/test_deck.dck")


class TestLexer:
    def test_tokenize_version(self):
        tokens = tokenize("VERSION 18")
        assert tokens[0].kind == TokenKind.VERSION
        assert tokens[0].payload == "18"

    def test_tokenize_simulation(self):
        tokens = tokenize("SIMULATION \t START\t STOP\t STEP\t! comment")
        t = [t for t in tokens if t.kind == TokenKind.SIMULATION][0]
        assert "START" in t.payload

    def test_tokenize_unit(self):
        tokens = tokenize("UNIT 2 TYPE 50\t PV/T")
        t = [t for t in tokens if t.kind == TokenKind.UNIT][0]
        assert "2" in t.payload
        assert "50" in t.payload

    def test_tokenize_studio_markup(self):
        tokens = tokenize("*$UNIT_NAME PV/T")
        assert tokens[0].kind == TokenKind.STUDIO_UNIT_NAME
        assert tokens[0].payload == "PV/T"

    def test_tokenize_studio_position(self):
        tokens = tokenize("*$POSITION 207 182")
        assert tokens[0].kind == TokenKind.STUDIO_POSITION
        assert tokens[0].payload == "207 182"

    def test_tokenize_comment_lines(self):
        for line in [
            "* This is a comment",
            "*** stars comment",
            "! exclamation comment",
            "*$# hash comment",
        ]:
            tokens = tokenize(line)
            assert tokens[0].kind == TokenKind.COMMENT, f"Failed for: {line}"

    def test_tokenize_link(self):
        tokens = tokenize("*!LINK 26:17")
        assert tokens[0].kind == TokenKind.LINK
        assert "26:17" in tokens[0].payload

    def test_tokenize_connection_set(self):
        tokens = tokenize("*!CONNECTION_SET 0:20:40:20:3:12632256:2:0:1:490,324")
        assert tokens[0].kind == TokenKind.LINK_CONNECTION_SET

    def test_tokenize_link_style_markers(self):
        tokens = tokenize("*!LINK_STYLE\n*!LINK_STYLE_END")
        kinds = [t.kind for t in tokens]
        assert TokenKind.LINK_STYLE in kinds
        assert TokenKind.LINK_STYLE_END in kinds

    def test_tokenize_data_line(self):
        tokens = tokenize("4.19\t\t! 4 Fluid Thermal Capacitance")
        assert tokens[0].kind == TokenKind.DATA_LINE
        assert "4.19" in tokens[0].payload

    def test_tokenize_blank_line(self):
        tokens = tokenize("\n")
        blanks = [t for t in tokens if t.kind == TokenKind.BLANK]
        assert len(blanks) > 0

    def test_tokenize_end(self):
        tokens = tokenize("END")
        assert tokens[0].kind == TokenKind.END

    def test_tokenize_assign(self):
        line = 'ASSIGN "C:\\path\\to\\file.tm2" 30'
        tokens = tokenize(line)
        assert tokens[0].kind == TokenKind.ASSIGN

    def test_tokenize_constants(self):
        tokens = tokenize("CONSTANTS 3")
        assert tokens[0].kind == TokenKind.CONSTANTS
        assert tokens[0].payload == "3"

    def test_tokenize_user_constants(self):
        text = "*$USER_CONSTANTS\nEQUATIONS 1\n*$USER_CONSTANTS_END"
        tokens = tokenize(text)
        kinds = [t.kind for t in tokens]
        assert TokenKind.USER_CONSTANTS in kinds
        assert TokenKind.USER_CONSTANTS_END in kinds

    def test_tokenize_case_insensitive(self):
        for line in ["version 18", "VERSION 18", "Version 18"]:
            tokens = tokenize(line)
            assert tokens[0].kind == TokenKind.VERSION

    def test_tokenize_full_deck(self):
        text = DCK_FILE.read_text()
        tokens = tokenize(text)
        kinds = {t.kind for t in tokens}
        assert TokenKind.VERSION in kinds
        assert TokenKind.UNIT in kinds
        assert TokenKind.PARAMETERS in kinds
        assert TokenKind.INPUTS in kinds
        assert TokenKind.END in kinds
        assert TokenKind.LINK in kinds

    def test_line_numbers_preserved(self):
        text = "VERSION 18\n\nUNIT 2 TYPE 50 PV/T"
        tokens = tokenize(text)
        version = [t for t in tokens if t.kind == TokenKind.VERSION][0]
        unit = [t for t in tokens if t.kind == TokenKind.UNIT][0]
        assert version.line_number == 1
        assert unit.line_number == 3


class TestParser:
    def test_parse_version(self):
        deck = parse("VERSION 18")
        assert deck.version is not None
        assert deck.version.version == "18"

    def test_parse_simulation(self):
        text = "SIMULATION START STOP STEP"
        deck = parse(text)
        assert deck.simulation is not None
        assert deck.simulation.start == "START"
        assert deck.simulation.stop == "STOP"
        assert deck.simulation.step == "STEP"

    def test_parse_tolerances(self):
        deck = parse("TOLERANCES 0.001 0.001")
        assert deck.tolerances is not None
        assert deck.tolerances.integration == 0.001

    def test_parse_limits(self):
        deck = parse("LIMITS 30 500 50")
        assert deck.limits is not None
        assert deck.limits.max_iterations == 30
        assert deck.limits.max_warnings == 500
        assert deck.limits.trace_limit == 50

    def test_parse_generic_statements(self):
        text = "DFQ 1\nWIDTH 80\nSOLVER 0 1 1\nNAN_CHECK 0"
        deck = parse(text)
        keywords = [s.keyword for s in deck.statements]
        assert "dfq" in keywords
        assert "width" in keywords
        assert "solver" in keywords
        assert "nan_check" in keywords

    def test_parse_constants_block(self):
        text = "CONSTANTS 3\nSTART=2880\nSTOP=3048\nSTEP=0.25"
        deck = parse(text)
        assert len(deck.constants_blocks) == 1
        block = deck.constants_blocks[0]
        assert len(block.constants) == 3
        assert block.constants[0].name == "START"
        assert block.constants[0].expression == "2880"

    def test_parse_equations_block(self):
        text = "EQUATIONS 1\nnPlots = (STOP-START)/168."
        deck = parse(text)
        assert len(deck.equation_blocks) == 1
        block = deck.equation_blocks[0]
        assert len(block.equations) == 1
        assert block.equations[0].name == "nPlots"
        assert "(STOP-START)/168." in block.equations[0].expression

    def test_parse_user_constants_block(self):
        text = (
            "*$USER_CONSTANTS\n"
            "EQUATIONS 1\n"
            "nPlots = (STOP-START)/168.\n"
            "*$USER_CONSTANTS_END"
        )
        deck = parse(text)
        assert len(deck.user_constants_blocks) == 1
        uc = deck.user_constants_blocks[0]
        assert uc.equations_block is not None
        assert len(uc.equations_block.equations) == 1

    def test_parse_unit_block(self):
        text = (
            "UNIT 2 TYPE 50\t PV/T\n"
            "*$UNIT_NAME PV/T\n"
            "*$MODEL .\\Type50d.tmf\n"
            "*$POSITION 207 182\n"
            "*$LAYER Main #\n"
            "PARAMETERS 3\n"
            "4\t\t! 1 Mode\n"
            "12\t\t! 2 Area\n"
            "0.7\t\t! 3 Efficiency\n"
            "INPUTS 2\n"
            "21,1 \t\t! connection\n"
            "0,0\t\t! unconnected\n"
            "*** INITIAL INPUT VALUES\n"
            "0 0.2\n"
        )
        deck = parse(text)
        assert len(deck.units) == 1
        ub = deck.units[0]
        assert ub.unit.unit_number == 2
        assert ub.unit.type_number == 50
        assert ub.unit.name == "PV/T"
        assert ub.parameters is not None
        assert len(ub.parameters.values) == 3
        assert ub.parameters.values[0] == "4"
        assert ub.inputs is not None
        assert len(ub.inputs.connections) == 2
        assert ub.inputs.connections[0].raw == "21,1"
        assert ub.inputs.connections[1].raw == "0,0"
        assert len(ub.inputs.initial_values) == 2

    def test_parse_derivatives(self):
        text = (
            "UNIT 14 TYPE 47\t battery bank\n"
            "PARAMETERS 1\n"
            "1\n"
            "INPUTS 1\n"
            "7,2\n"
            "*** INITIAL INPUT VALUES\n"
            "0\n"
            "DERIVATIVES 1\n"
            "20\t\t! 1 State of charge1\n"
        )
        deck = parse(text)
        assert len(deck.units) == 1
        assert deck.units[0].derivatives is not None
        assert deck.units[0].derivatives.values == ("20",)

    def test_parse_external_files(self):
        text = (
            "UNIT 4 TYPE 15\t Boulder, CO\n"
            "PARAMETERS 1\n"
            "2\n"
            '*** External files\n'
            'ASSIGN "C:\\path\\file.tm2" 30\n'
        )
        deck = parse(text)
        assert len(deck.units) == 1
        assert len(deck.units[0].external_files) == 1
        ef = deck.units[0].external_files[0]
        assert ef.path == "C:\\path\\file.tm2"
        assert ef.logical_unit == 30

    def test_parse_labels(self):
        text = (
            "UNIT 3 TYPE 65\t LIQUID SIDE\n"
            "PARAMETERS 1\n"
            "5\n"
            "INPUTS 1\n"
            "4,1\n"
            "*** INITIAL INPUT VALUES\n"
            "T_ambDB\n"
            "LABELS  3\n"
            '"Temperature [C]"\n'
            '"Flow Rate [kg/h]"\n'
            '"liquid loop"\n'
        )
        deck = parse(text)
        assert deck.units[0].labels is not None
        assert deck.units[0].labels.count == 3
        assert len(deck.units[0].labels.values) == 3

    def test_parse_link_styles(self):
        text = (
            "*!LINK_STYLE\n"
            "*!LINK 26:17\n"
            "*!CONNECTION_SET 0:20:40:20:3:12632256:2:0:1:490,324\n"
            "*!LINK 16:26\n"
            "*!CONNECTION_SET 0:40:40:20:2:12632256:2:0:1:645,216\n"
            "*!LINK_STYLE_END\n"
        )
        deck = parse(text)
        assert len(deck.links) == 2
        assert deck.links[0].u == 26
        assert deck.links[0].v == 17
        assert deck.links[1].u == 16
        assert deck.links[1].v == 26

    def test_parse_equation_block_with_studio(self):
        text = (
            "EQUATIONS 1\n"
            "pLoad = 500.*3.6*[12,1]\n"
            "*$UNIT_NAME pLoad\n"
            "*$LAYER Main\n"
            "*$POSITION 573 602\n"
            "*$UNIT_NUMBER 13\n"
        )
        deck = parse(text)
        assert len(deck.equation_blocks) == 1
        eq = deck.equation_blocks[0]
        assert eq.equations[0].name == "pLoad"

    def test_parse_full_deck(self):
        text = DCK_FILE.read_text()
        deck = parse(text)

        # Version
        assert deck.version is not None
        assert deck.version.version == "18"

        # Control cards
        assert deck.simulation is not None
        assert deck.tolerances is not None
        assert deck.limits is not None
        assert len(deck.statements) > 0

        # Constants
        assert len(deck.constants_blocks) >= 1
        total_constants = sum(
            len(b.constants) for b in deck.constants_blocks
        )
        assert total_constants == 3  # START, STOP, STEP

        # User constants (equation block)
        assert len(deck.user_constants_blocks) >= 1

        # Units (TrnsysModel components)
        assert len(deck.units) >= 15

        # Check a specific unit
        unit2 = next(u for u in deck.units if u.unit.unit_number == 2)
        assert unit2.unit.type_number == 50
        assert unit2.unit.name == "PV/T"
        assert unit2.parameters is not None
        assert len(unit2.parameters.values) == 13
        assert unit2.inputs is not None
        assert len(unit2.inputs.connections) == 8

        # Equation blocks (pLoad, flow control)
        assert len(deck.equation_blocks) >= 2

        # Links
        assert len(deck.links) > 0

    def test_parse_multiple_units(self):
        text = DCK_FILE.read_text()
        deck = parse(text)
        unit_numbers = [u.unit.unit_number for u in deck.units]
        # Check that we got all expected units from the test deck
        for expected in [2, 3, 4, 5, 7, 9, 10, 11, 12, 14, 15, 16, 17, 18, 21, 23, 24, 25, 26]:
            assert expected in unit_numbers, f"Unit {expected} not found"
