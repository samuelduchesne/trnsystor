"""Intermediate representation dataclasses for parsed .dck content.

These frozen dataclasses capture the raw text of a .dck file in a
structured form *without* constructing any domain objects.  They carry
``SourceLocation`` so that errors discovered later (during resolution)
can report the originating line number.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Position in the source .dck file."""

    line: int
    col: int = 0


# ---------------------------------------------------------------------------
# Control-card tokens
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedVersion:
    version: str
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedSimulation:
    start: str
    stop: str
    step: str
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedTolerances:
    integration: float
    convergence: float
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedLimits:
    max_iterations: int
    max_warnings: int
    trace_limit: int
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedStatement:
    """Generic single-keyword statement (DFQ, WIDTH, SOLVER, etc.)."""

    keyword: str
    args: tuple[str, ...]
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedConstant:
    name: str
    expression: str
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedConstantsBlock:
    constants: tuple[ParsedConstant, ...]
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedEquation:
    name: str
    expression: str
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedEquationsBlock:
    equations: tuple[ParsedEquation, ...]
    loc: SourceLocation
    studio: tuple[ParsedStudioMarkup, ...] = ()


# ---------------------------------------------------------------------------
# Studio markup
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedStudioMarkup:
    """One studio comment line: *$UNIT_NAME, *$MODEL, etc."""

    key: str  # "unit_name", "model", "position", "layer", "unit_number"
    value: str
    loc: SourceLocation


# ---------------------------------------------------------------------------
# Unit (component) blocks
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedUnit:
    unit_number: int
    type_number: int
    name: str
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedInputConnection:
    """One input line: ``21,1`` or ``TdbAmb`` or ``0,0``."""

    raw: str
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedInputs:
    connections: tuple[ParsedInputConnection, ...]
    initial_values: tuple[str, ...]
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedParameters:
    values: tuple[str, ...]
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedDerivatives:
    values: tuple[str, ...]
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedExternalFile:
    path: str
    logical_unit: int
    loc: SourceLocation


@dataclass(frozen=True, slots=True)
class ParsedLabels:
    count: int
    values: tuple[str, ...]
    loc: SourceLocation


@dataclass(slots=True)
class ParsedUnitBlock:
    """All data for one ``UNIT n TYPE m name`` and its subsequent sections.

    Mutable during parsing, then treated as read-only after the parser
    finalizes it into the ``ParsedDeck.units`` list.
    """

    unit: ParsedUnit
    studio: tuple[ParsedStudioMarkup, ...] = ()
    parameters: ParsedParameters | None = None
    inputs: ParsedInputs | None = None
    derivatives: ParsedDerivatives | None = None
    external_files: list[ParsedExternalFile] = field(default_factory=list)
    labels: ParsedLabels | None = None


# ---------------------------------------------------------------------------
# User-constants wrapper (equation blocks inside *$USER_CONSTANTS)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedUserConstantsBlock:
    equations_block: ParsedEquationsBlock | None
    studio: tuple[ParsedStudioMarkup, ...]
    loc: SourceLocation


# ---------------------------------------------------------------------------
# Link styles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedLink:
    u: int
    v: int
    connection_set: str  # raw CONNECTION_SET payload
    loc: SourceLocation


# ---------------------------------------------------------------------------
# Top-level result
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ParsedDeck:
    """Complete parsed representation of a .dck file."""

    version: ParsedVersion | None = None
    simulation: ParsedSimulation | None = None
    tolerances: ParsedTolerances | None = None
    limits: ParsedLimits | None = None
    statements: list[ParsedStatement] = field(default_factory=list)
    constants_blocks: list[ParsedConstantsBlock] = field(default_factory=list)
    equation_blocks: list[ParsedEquationsBlock] = field(default_factory=list)
    user_constants_blocks: list[ParsedUserConstantsBlock] = field(
        default_factory=list
    )
    units: list[ParsedUnitBlock] = field(default_factory=list)
    links: list[ParsedLink] = field(default_factory=list)
