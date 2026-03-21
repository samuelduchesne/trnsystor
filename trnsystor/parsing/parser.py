"""Single-pass state-machine parser for TRNSYS .dck files.

Consumes a token stream from :func:`~trnsystor.parsing.lexer.tokenize`
and produces a :class:`ParsedDeck` tree of dataclasses.

No domain objects are created — only raw strings, ints, floats, and
:class:`~trnsystor.parsing.tokens.SourceLocation` instances.
"""

from __future__ import annotations

import re
from enum import Enum, auto

from trnsystor.parsing.lexer import Token, TokenKind, tokenize
from trnsystor.parsing.tokens import (
    ParsedConstant,
    ParsedConstantsBlock,
    ParsedDeck,
    ParsedDerivatives,
    ParsedEquation,
    ParsedEquationsBlock,
    ParsedExternalFile,
    ParsedInputConnection,
    ParsedInputs,
    ParsedLabels,
    ParsedLimits,
    ParsedLink,
    ParsedParameters,
    ParsedSimulation,
    ParsedStatement,
    ParsedStudioMarkup,
    ParsedTolerances,
    ParsedUnit,
    ParsedUnitBlock,
    ParsedUserConstantsBlock,
    ParsedVersion,
    SourceLocation,
)


class DeckParseError(Exception):
    """Error raised when the .dck parser encounters invalid input."""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        prefix = f"Line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")


class _State(Enum):
    TOP_LEVEL = auto()
    IN_CONSTANTS = auto()
    IN_EQUATIONS = auto()
    IN_UNIT = auto()
    IN_PARAMETERS = auto()
    IN_INPUTS = auto()
    IN_INITIAL_VALUES = auto()
    IN_USER_CONSTANTS = auto()
    IN_LINK = auto()
    IN_LABELS = auto()
    IN_LINK_STYLES = auto()


# Regex for UNIT line payload: "2 TYPE 50 PV/T" or "2 50 PV/T"
_UNIT_RE = re.compile(
    r"(\d+)\s+(?:type\s+)?(\d+)\s*(.*)", re.IGNORECASE
)

# Regex for ASSIGN payload: '"path" logical_unit'
_ASSIGN_RE = re.compile(r'"([^"]+)"\s+(\d+)')


def parse(text: str) -> ParsedDeck:
    """Parse a .dck file string into a :class:`ParsedDeck`.

    Args:
        text: The full .dck file content.

    Returns:
        A :class:`ParsedDeck` containing the complete parsed structure.

    Raises:
        DeckParseError: On unrecognized or misplaced tokens.
    """
    tokens = tokenize(text)
    return _Parser(tokens).run()


class _Parser:
    """Internal state-machine parser."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._state = _State.TOP_LEVEL
        self._deck = ParsedDeck()

        # Current unit block being assembled (mutable)
        self._current_unit: ParsedUnitBlock | None = None
        self._current_studio: list[ParsedStudioMarkup] = []

        # Counters for expected data lines
        self._expected_count = 0
        self._collected: list[str] = []
        self._collecting_derivatives = False

        # For inputs: separate connections and initial values
        self._input_connections: list[ParsedInputConnection] = []
        self._input_initial_values: list[str] = []
        self._input_count = 0

        # For user constants blocks
        self._uc_equations: ParsedEquationsBlock | None = None
        self._uc_studio: list[ParsedStudioMarkup] = []
        self._uc_loc: SourceLocation | None = None
        self._uc_return = False

        # For links
        self._link_u = 0
        self._link_v = 0
        self._link_loc: SourceLocation | None = None

        # For labels
        self._label_count = 0
        self._label_values: list[str] = []

    def run(self) -> ParsedDeck:
        """Run the parser over all tokens."""
        while self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            self._dispatch(token)
            self._pos += 1

        # Finalize any open unit block
        self._finalize_unit()

        return self._deck

    def _loc(self, token: Token) -> SourceLocation:
        return SourceLocation(token.line_number)

    def _dispatch(self, token: Token) -> None:
        """Route token to the appropriate handler based on current state."""
        if token.kind in (TokenKind.BLANK, TokenKind.COMMENT):
            return

        handler = {
            _State.IN_LINK_STYLES: self._handle_link_styles,
            _State.IN_CONSTANTS: self._handle_in_constants,
            _State.IN_EQUATIONS: self._handle_in_equations,
            _State.IN_PARAMETERS: self._handle_in_parameters,
            _State.IN_INPUTS: self._handle_in_inputs,
            _State.IN_INITIAL_VALUES: self._handle_in_initial_values,
            _State.IN_LABELS: self._handle_in_labels,
            _State.IN_LINK: self._handle_in_link,
            _State.IN_USER_CONSTANTS: self._handle_in_user_constants,
            _State.IN_UNIT: self._handle_unit_state,
            _State.TOP_LEVEL: self._handle_top_level,
        }.get(self._state, self._handle_top_level)
        handler(token)

    # -----------------------------------------------------------------
    # Top-level handlers
    # -----------------------------------------------------------------

    def _handle_top_level(self, token: Token) -> None:
        loc = self._loc(token)

        if token.kind == TokenKind.VERSION:
            self._deck.version = ParsedVersion(
                token.payload.strip(), loc
            )

        elif token.kind == TokenKind.SIMULATION:
            parts = token.payload.split()
            if len(parts) >= 3:
                self._deck.simulation = ParsedSimulation(
                    parts[0], parts[1], parts[2], loc
                )

        elif token.kind == TokenKind.TOLERANCES:
            parts = token.payload.split()
            if len(parts) >= 2:
                self._deck.tolerances = ParsedTolerances(
                    float(parts[0]), float(parts[1]), loc
                )

        elif token.kind == TokenKind.LIMITS:
            parts = token.payload.split()
            if len(parts) >= 3:
                self._deck.limits = ParsedLimits(
                    int(parts[0]), int(parts[1]), int(parts[2]), loc
                )

        elif token.kind in (
            TokenKind.DFQ,
            TokenKind.WIDTH,
            TokenKind.LIST,
            TokenKind.SOLVER,
            TokenKind.NAN_CHECK,
            TokenKind.OVERWRITE_CHECK,
            TokenKind.TIME_REPORT,
            TokenKind.EQSOLVER,
        ):
            self._deck.statements.append(
                ParsedStatement(
                    token.kind.name.lower(),
                    tuple(token.payload.split()),
                    loc,
                )
            )

        elif token.kind == TokenKind.CONSTANTS:
            self._start_counting(token, _State.IN_CONSTANTS)

        elif token.kind == TokenKind.EQUATIONS:
            self._start_counting(token, _State.IN_EQUATIONS)

        elif token.kind == TokenKind.UNIT:
            self._start_unit(token)

        elif token.kind == TokenKind.USER_CONSTANTS:
            self._uc_equations = None
            self._uc_studio = []
            self._uc_loc = loc
            self._state = _State.IN_USER_CONSTANTS

        elif token.kind == TokenKind.LINK_STYLE:
            self._state = _State.IN_LINK_STYLES

        elif token.kind == TokenKind.LINK:
            self._handle_link_start(token)

        elif token.kind == TokenKind.END:
            pass

        elif token.kind in (
            TokenKind.STUDIO_UNIT_NAME,
            TokenKind.STUDIO_MODEL,
            TokenKind.STUDIO_POSITION,
            TokenKind.STUDIO_LAYER,
            TokenKind.STUDIO_UNIT_NUMBER,
        ):
            self._collect_studio_markup(token, loc)

    # -----------------------------------------------------------------
    # State: IN_UNIT
    # -----------------------------------------------------------------

    def _handle_unit_state(self, token: Token) -> None:
        loc = self._loc(token)

        if token.kind in (
            TokenKind.STUDIO_UNIT_NAME,
            TokenKind.STUDIO_MODEL,
            TokenKind.STUDIO_POSITION,
            TokenKind.STUDIO_LAYER,
            TokenKind.STUDIO_UNIT_NUMBER,
        ):
            self._collect_studio_markup(token, loc)

        elif token.kind == TokenKind.PARAMETERS:
            self._start_counting(token, _State.IN_PARAMETERS)

        elif token.kind == TokenKind.INPUTS:
            count_str = token.payload.strip()
            count = int(count_str) if count_str else 0
            self._input_count = count
            self._input_connections = []
            self._input_initial_values = []
            self._state = _State.IN_INPUTS

        elif token.kind == TokenKind.DERIVATIVES:
            self._start_counting(token, _State.IN_PARAMETERS)
            self._collecting_derivatives = True

        elif token.kind == TokenKind.ASSIGN:
            m = _ASSIGN_RE.match(token.payload)
            if m and self._current_unit:
                self._current_unit.external_files.append(
                    ParsedExternalFile(m.group(1), int(m.group(2)), loc)
                )

        elif token.kind == TokenKind.LABELS:
            count_str = token.payload.strip()
            self._label_count = int(count_str) if count_str else 0
            self._label_values = []
            self._state = _State.IN_LABELS

        elif token.kind == TokenKind.UNIT:
            self._start_unit(token)

        elif token.kind == TokenKind.EQUATIONS:
            self._finalize_unit()
            self._start_counting(token, _State.IN_EQUATIONS)

        elif token.kind in (TokenKind.LINK, TokenKind.LINK_STYLE):
            self._finalize_unit()
            if token.kind == TokenKind.LINK:
                self._handle_link_start(token)
            else:
                self._state = _State.IN_LINK_STYLES

        elif token.kind == TokenKind.END:
            self._finalize_unit()
            self._state = _State.TOP_LEVEL

    # -----------------------------------------------------------------
    # IN_CONSTANTS
    # -----------------------------------------------------------------

    def _handle_in_constants(self, token: Token) -> None:
        if token.kind == TokenKind.DATA_LINE:
            self._collected.append(token.payload)
            if len(self._collected) >= self._expected_count:
                self._finish_constants_block(token)
        else:
            self._finish_constants_block(token)
            self._dispatch(token)

    def _finish_constants_block(self, token: Token) -> None:
        constants = []
        for line in self._collected:
            if "=" in line:
                name, _, expr = line.partition("=")
                constants.append(
                    ParsedConstant(name.strip(), expr.strip(), self._loc(token))
                )
        loc = SourceLocation(token.line_number - len(self._collected))
        self._deck.constants_blocks.append(
            ParsedConstantsBlock(tuple(constants), loc)
        )
        self._state = _State.TOP_LEVEL

    # -----------------------------------------------------------------
    # IN_EQUATIONS
    # -----------------------------------------------------------------

    def _handle_in_equations(self, token: Token) -> None:
        if token.kind == TokenKind.DATA_LINE:
            self._collected.append(token.payload)
            if len(self._collected) >= self._expected_count:
                self._finish_equations_block(token)
        else:
            self._finish_equations_block(token)
            self._dispatch(token)

    def _finish_equations_block(self, token: Token) -> None:
        equations = []
        for line in self._collected:
            if "=" in line:
                name, _, expr = line.partition("=")
                equations.append(
                    ParsedEquation(name.strip(), expr.strip(), self._loc(token))
                )
        loc = SourceLocation(token.line_number - len(self._collected))
        block = ParsedEquationsBlock(tuple(equations), loc)

        if self._uc_return:
            self._uc_equations = block
            self._uc_return = False
            self._state = _State.IN_USER_CONSTANTS
        else:
            self._deck.equation_blocks.append(block)
            self._state = _State.TOP_LEVEL

    # -----------------------------------------------------------------
    # IN_PARAMETERS (also used for DERIVATIVES)
    # -----------------------------------------------------------------

    def _handle_in_parameters(self, token: Token) -> None:
        if token.kind == TokenKind.DATA_LINE:
            for val in token.payload.split():
                self._collected.append(val)
            if len(self._collected) >= self._expected_count:
                self._finish_parameters()
        else:
            self._finish_parameters()
            if self._state == _State.IN_UNIT:
                self._handle_unit_state(token)
            else:
                self._dispatch(token)

    def _finish_parameters(self) -> None:
        if self._current_unit is None:
            self._state = _State.TOP_LEVEL
            return

        values = tuple(self._collected[: self._expected_count])

        if self._collecting_derivatives:
            self._current_unit.derivatives = ParsedDerivatives(
                values, SourceLocation(0)
            )
            self._collecting_derivatives = False
        else:
            self._current_unit.parameters = ParsedParameters(
                values, SourceLocation(0)
            )

        self._state = _State.IN_UNIT

    # -----------------------------------------------------------------
    # IN_INPUTS → IN_INITIAL_VALUES
    # -----------------------------------------------------------------

    def _handle_in_inputs(self, token: Token) -> None:
        if token.kind == TokenKind.DATA_LINE:
            loc = self._loc(token)
            for val in token.payload.split():
                self._input_connections.append(
                    ParsedInputConnection(val, loc)
                )
            if len(self._input_connections) >= self._input_count:
                self._state = _State.IN_INITIAL_VALUES
        else:
            self._finish_inputs()
            if self._state == _State.IN_UNIT:
                self._handle_unit_state(token)
            else:
                self._dispatch(token)

    def _handle_in_initial_values(self, token: Token) -> None:
        if token.kind == TokenKind.DATA_LINE:
            for val in token.payload.split():
                self._input_initial_values.append(val)
        else:
            self._finish_inputs()
            if self._state == _State.IN_UNIT:
                self._handle_unit_state(token)
            else:
                self._dispatch(token)

    def _finish_inputs(self) -> None:
        if self._current_unit is None:
            self._state = _State.TOP_LEVEL
            return
        self._current_unit.inputs = ParsedInputs(
            tuple(self._input_connections),
            tuple(self._input_initial_values),
            SourceLocation(0),
        )
        self._state = _State.IN_UNIT

    # -----------------------------------------------------------------
    # IN_LABELS
    # -----------------------------------------------------------------

    def _handle_in_labels(self, token: Token) -> None:
        if token.kind == TokenKind.DATA_LINE:
            self._label_values.append(token.payload)
            if len(self._label_values) >= self._label_count:
                self._finish_labels()
        else:
            self._finish_labels()
            if self._state == _State.IN_UNIT:
                self._handle_unit_state(token)
            else:
                self._dispatch(token)

    def _finish_labels(self) -> None:
        if self._current_unit is not None:
            self._current_unit.labels = ParsedLabels(
                self._label_count,
                tuple(self._label_values),
                SourceLocation(0),
            )
        self._state = _State.IN_UNIT

    # -----------------------------------------------------------------
    # IN_USER_CONSTANTS
    # -----------------------------------------------------------------

    def _handle_in_user_constants(self, token: Token) -> None:
        loc = self._loc(token)

        if token.kind == TokenKind.USER_CONSTANTS_END:
            self._deck.user_constants_blocks.append(
                ParsedUserConstantsBlock(
                    self._uc_equations,
                    tuple(self._uc_studio),
                    self._uc_loc or loc,
                )
            )
            self._state = _State.TOP_LEVEL

        elif token.kind == TokenKind.EQUATIONS:
            self._start_counting(token, _State.IN_EQUATIONS)
            self._uc_return = True

        elif token.kind in (
            TokenKind.STUDIO_UNIT_NAME,
            TokenKind.STUDIO_POSITION,
            TokenKind.STUDIO_LAYER,
            TokenKind.STUDIO_UNIT_NUMBER,
        ):
            self._uc_studio.append(
                ParsedStudioMarkup(
                    token.kind.name.lower().removeprefix("studio_"),
                    token.payload,
                    loc,
                )
            )

    # -----------------------------------------------------------------
    # IN_LINK / IN_LINK_STYLES
    # -----------------------------------------------------------------

    def _handle_link_start(self, token: Token) -> None:
        parts = token.payload.strip().split(":")
        if len(parts) >= 2:
            self._link_u = int(parts[0])
            self._link_v = int(parts[1])
            self._link_loc = self._loc(token)
            self._state = _State.IN_LINK

    def _handle_in_link(self, token: Token) -> None:
        if token.kind == TokenKind.LINK_CONNECTION_SET:
            self._deck.links.append(
                ParsedLink(
                    self._link_u, self._link_v,
                    token.payload,
                    self._link_loc or self._loc(token),
                )
            )
            self._state = _State.TOP_LEVEL
        elif token.kind == TokenKind.LINK:
            self._handle_link_start(token)
        else:
            self._state = _State.TOP_LEVEL
            self._dispatch(token)

    def _handle_link_styles(self, token: Token) -> None:
        if token.kind == TokenKind.LINK_STYLE_END:
            self._state = _State.TOP_LEVEL
        elif token.kind == TokenKind.LINK:
            self._handle_link_start(token)
        elif token.kind == TokenKind.LINK_CONNECTION_SET:
            self._deck.links.append(
                ParsedLink(
                    self._link_u, self._link_v,
                    token.payload,
                    self._link_loc or self._loc(token),
                )
            )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _start_counting(self, token: Token, state: _State) -> None:
        """Begin collecting N data lines for constants/equations/parameters."""
        count_str = token.payload.strip()
        self._expected_count = int(count_str) if count_str else 0
        self._collected = []
        self._state = state

    def _start_unit(self, token: Token) -> None:
        """Start a new UNIT block, finalizing any previous one."""
        self._finalize_unit()
        m = _UNIT_RE.match(token.payload)
        if m:
            self._current_unit = ParsedUnitBlock(
                unit=ParsedUnit(
                    int(m.group(1)), int(m.group(2)),
                    m.group(3).strip(), self._loc(token),
                ),
            )
            self._current_studio = []
            self._state = _State.IN_UNIT

    def _collect_studio_markup(self, token: Token, loc: SourceLocation) -> None:
        """Collect a studio markup token into the current studio list."""
        self._current_studio.append(
            ParsedStudioMarkup(
                token.kind.name.lower().removeprefix("studio_"),
                token.payload,
                loc,
            )
        )

    def _finalize_unit(self) -> None:
        """Flush pending state and push the current unit block onto the deck."""
        if self._state in (_State.IN_INPUTS, _State.IN_INITIAL_VALUES):
            self._finish_inputs()
        if self._state == _State.IN_PARAMETERS:
            self._finish_parameters()
        if self._state == _State.IN_LABELS:
            self._finish_labels()
        if self._current_unit is not None:
            self._current_unit.studio = tuple(self._current_studio)
            self._deck.units.append(self._current_unit)
            self._current_unit = None
            self._current_studio = []
