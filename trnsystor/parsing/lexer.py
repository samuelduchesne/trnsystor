"""Lexer for TRNSYS .dck files.

Classifies each line into a :class:`Token` with O(1) keyword dispatch.
Replaces the previous approach of trying 28 compiled regexes per line.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    """Classification of a .dck file line."""

    # Control cards
    VERSION = auto()
    SIMULATION = auto()
    TOLERANCES = auto()
    LIMITS = auto()
    DFQ = auto()
    WIDTH = auto()
    LIST = auto()
    SOLVER = auto()
    NAN_CHECK = auto()
    OVERWRITE_CHECK = auto()
    TIME_REPORT = auto()
    EQSOLVER = auto()
    CONSTANTS = auto()
    EQUATIONS = auto()
    END = auto()

    # Component definition
    UNIT = auto()
    PARAMETERS = auto()
    INPUTS = auto()
    LABELS = auto()
    DERIVATIVES = auto()
    ASSIGN = auto()

    # Studio markup (*$ prefixed)
    STUDIO_UNIT_NAME = auto()
    STUDIO_MODEL = auto()
    STUDIO_POSITION = auto()
    STUDIO_LAYER = auto()
    STUDIO_UNIT_NUMBER = auto()
    USER_CONSTANTS = auto()
    USER_CONSTANTS_END = auto()

    # Link styles (*! prefixed)
    LINK = auto()
    LINK_CONNECTION_SET = auto()
    LINK_STYLE = auto()
    LINK_STYLE_END = auto()

    # Catch-all
    DATA_LINE = auto()
    COMMENT = auto()
    BLANK = auto()


@dataclass(frozen=True, slots=True)
class Token:
    """A classified line from a .dck file."""

    kind: TokenKind
    payload: str  # text after the keyword (stripped of comments)
    line_number: int
    raw: str  # full original line


def _strip_comment(text: str) -> str:
    """Remove trailing ``! comment`` from a line, preserving quoted strings."""
    # Simple approach: split on first '!' not inside quotes
    in_quote = False
    for i, ch in enumerate(text):
        if ch == '"':
            in_quote = not in_quote
        elif ch == "!" and not in_quote:
            return text[:i].rstrip()
    return text.rstrip()


# Keyword dispatch table: lowered first word → TokenKind
_KEYWORD_MAP: dict[str, TokenKind] = {
    "version": TokenKind.VERSION,
    "simulation": TokenKind.SIMULATION,
    "tolerances": TokenKind.TOLERANCES,
    "limits": TokenKind.LIMITS,
    "dfq": TokenKind.DFQ,
    "width": TokenKind.WIDTH,
    "list": TokenKind.LIST,
    "solver": TokenKind.SOLVER,
    "nan_check": TokenKind.NAN_CHECK,
    "overwrite_check": TokenKind.OVERWRITE_CHECK,
    "time_report": TokenKind.TIME_REPORT,
    "eqsolver": TokenKind.EQSOLVER,
    "constants": TokenKind.CONSTANTS,
    "equations": TokenKind.EQUATIONS,
    "unit": TokenKind.UNIT,
    "parameters": TokenKind.PARAMETERS,
    "inputs": TokenKind.INPUTS,
    "labels": TokenKind.LABELS,
    "derivatives": TokenKind.DERIVATIVES,
    "assign": TokenKind.ASSIGN,
    "nolist": TokenKind.LIST,  # NOLIST maps to LIST for parsing purposes
    "map": TokenKind.LIST,  # MAP maps to LIST for parsing purposes
    "nocheck": TokenKind.LIST,  # NOCHECK maps to LIST for parsing purposes
    "end": TokenKind.END,
}

# Studio prefix dispatch: lowered text after *$ → TokenKind
_STUDIO_MAP: dict[str, TokenKind] = {
    "unit_name": TokenKind.STUDIO_UNIT_NAME,
    "model": TokenKind.STUDIO_MODEL,
    "position": TokenKind.STUDIO_POSITION,
    "layer": TokenKind.STUDIO_LAYER,
    "unit_number": TokenKind.STUDIO_UNIT_NUMBER,
    "user_constants": TokenKind.USER_CONSTANTS,
    "user_constants_end": TokenKind.USER_CONSTANTS_END,
}


def _classify_line(line: str, line_number: int) -> Token:
    """Classify a single line into a Token."""
    raw = line
    stripped = line.strip()

    # Blank lines
    if not stripped:
        return Token(TokenKind.BLANK, "", line_number, raw)

    # Studio markup: *$KEY value
    if stripped.startswith("*$"):
        rest = stripped[2:]
        # Find the keyword (everything up to first space)
        space_idx = rest.find(" ")
        if space_idx == -1:
            key = rest.lower()
            value = ""
        else:
            key = rest[:space_idx].lower()
            value = rest[space_idx + 1:].strip()
        kind = _STUDIO_MAP.get(key)
        if kind is not None:
            return Token(kind, value, line_number, raw)
        # Unknown *$ line — treat as comment
        return Token(TokenKind.COMMENT, stripped, line_number, raw)

    # Link markup: *!LINK, *!CONNECTION_SET, *!LINK_STYLE, *!LINK_STYLE_END
    if stripped.startswith("*!"):
        rest_words = stripped[2:].split()
        upper = rest_words[0].upper() if rest_words else ""
        if upper == "LINK":
            payload = stripped[2:].split(maxsplit=1)
            return Token(
                TokenKind.LINK,
                payload[1] if len(payload) > 1 else "",
                line_number,
                raw,
            )
        if upper == "CONNECTION_SET":
            payload = stripped[2:].split(maxsplit=1)
            return Token(
                TokenKind.LINK_CONNECTION_SET,
                payload[1] if len(payload) > 1 else "",
                line_number,
                raw,
            )
        if upper == "LINK_STYLE":
            return Token(TokenKind.LINK_STYLE, "", line_number, raw)
        if upper == "LINK_STYLE_END":
            return Token(TokenKind.LINK_STYLE_END, "", line_number, raw)
        return Token(TokenKind.COMMENT, stripped, line_number, raw)

    # Comment lines: start with *, !
    if stripped.startswith(("*", "!")):
        return Token(TokenKind.COMMENT, stripped, line_number, raw)

    # Keyword dispatch
    content = _strip_comment(stripped)
    words = content.split()
    first_word = words[0].lower() if words else ""

    kind = _KEYWORD_MAP.get(first_word)
    if kind is not None:
        # Payload is everything after the keyword
        rest = content[len(first_word):].strip()
        return Token(kind, rest, line_number, raw)

    # Data line (parameter values, equation expressions, etc.)
    return Token(TokenKind.DATA_LINE, content, line_number, raw)


def tokenize(text: str) -> list[Token]:
    """Tokenize a .dck file into a list of classified lines.

    Args:
        text: The full .dck file content as a string.

    Returns:
        A list of :class:`Token` objects, one per input line (including blanks).
    """
    tokens: list[Token] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        token = _classify_line(line, line_number)
        tokens.append(token)
    return tokens
