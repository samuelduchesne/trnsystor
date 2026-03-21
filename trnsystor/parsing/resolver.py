"""Resolver: builds domain objects from a ParsedDeck.

Takes the intermediate representation produced by
:func:`~trnsystor.parsing.parser.parse` and constructs the actual
:class:`~trnsystor.deck.Deck` with fully-resolved connections.

The resolver performs two sweeps over the parsed data:

1. **Build** — create all components (TrnsysModel, EquationCollection,
   ConstantCollection) and control cards from the IR.
2. **Connect** — resolve input connections now that all components exist.

This replaces the old two-full-pass parsing strategy with one parse
(already done) plus one in-memory sweep for connections.
"""

from __future__ import annotations

import contextlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from shapely.geometry import LineString

from trnsystor.anchorpoint import AnchorPoint
from trnsystor.collections.constant import ConstantCollection
from trnsystor.collections.equation import EquationCollection
from trnsystor.context import DeckContext
from trnsystor.controlcards import ControlCards
from trnsystor.linkstyle import _studio_to_linestyle
from trnsystor.name import Name
from trnsystor.statement import (
    DFQ,
    Constant,
    End,
    EqSolver,
    Equation,
    Limits,
    List,
    NaNCheck,
    OverwriteCheck,
    Simulation,
    Solver,
    TimeReport,
    Tolerances,
    Version,
    Width,
)
from trnsystor.trnsysmodel import TrnsysModel
from trnsystor.utils import get_rgb_from_int

if TYPE_CHECKING:
    from trnsystor.component import Component
    from trnsystor.deck import Deck
    from trnsystor.parsing.tokens import (
        ParsedDeck,
        ParsedEquationsBlock,
        ParsedLink,
        ParsedStudioMarkup,
        ParsedUnitBlock,
        ParsedUserConstantsBlock,
    )

log = logging.getLogger(__name__)

# CONNECTION_SET format regex
_CONNECTION_SET_RE = re.compile(
    r"(?P<u1>\d+):(?P<u2>\d+):"
    r"(?P<v1>\d+):(?P<v2>\d+):"
    r"(?P<order>[^:]*):(?P<color>[^:]*):(?P<linestyle>[^:]*):"
    r"(?P<linewidth>[^:]*):(?P<ignored>[^:]*):(?P<path>.*)"
)


def _find_closest(mappinglist, coordinate):
    """Find the closest point in mappinglist to coordinate."""
    from shapely.geometry import Point

    return min(
        mappinglist,
        key=lambda x: Point(x).distance(Point(coordinate)),
    )


def resolve(
    parsed: ParsedDeck,
    proforma_root: Path | str | None = None,
    ctx: DeckContext | None = None,
    name: str = "unnamed",
    **deck_kwargs,
) -> Deck:
    """Build a :class:`Deck` from a :class:`ParsedDeck`.

    Args:
        parsed: The parsed intermediate representation.
        proforma_root: Directory containing XML proformas.
        ctx: Scoped context. A fresh one is created if None.
        name: Deck name.
        **deck_kwargs: Extra keyword arguments for the Deck constructor.

    Returns:
        A fully-resolved :class:`Deck` with components and connections.
    """
    import itertools

    from trnsystor.deck import Deck

    if ctx is None:
        ctx = DeckContext(unit_counter=itertools.count(100_000))
    proforma_root = Path.cwd() if proforma_root is None else Path(proforma_root)

    # Phase 1: Build control cards
    cc = _build_control_cards(parsed, ctx)

    # Phase 2: Build all components
    dck = Deck(control_cards=cc, name=name, ctx=ctx, **deck_kwargs)
    _build_components(parsed, dck, proforma_root, ctx)

    # Phase 3: Resolve connections (inputs referencing other units)
    _resolve_connections(parsed, dck)

    # Phase 4: Apply link styles
    _apply_link_styles(parsed, dck)

    return dck


def _build_control_cards(parsed: ParsedDeck, ctx: DeckContext) -> ControlCards:
    """Build ControlCards from the parsed IR."""
    cc = ControlCards()

    if parsed.version:
        cc.set_statement(Version.from_string(parsed.version.version))

    # Constants blocks → ConstantCollection on the control cards
    for block in parsed.constants_blocks:
        cb = ConstantCollection(ctx=ctx)
        for pc in block.constants:
            cb.update(
                Constant.from_expression(
                    f"{pc.name}={pc.expression}", ctx=ctx
                )
            )
        cc.set_statement(cb)

    if parsed.simulation:
        s = parsed.simulation
        # start/stop/step may be constant names or literal numbers
        def _parse_sim_val(val: str) -> int | Constant:
            try:
                return int(val)
            except ValueError:
                return Constant(val, ctx=ctx)

        start, stop, step = (
            _parse_sim_val(v) for v in (s.start, s.stop, s.step)
        )
        cc.set_statement(Simulation(start, stop, step))  # type: ignore[arg-type]

    if parsed.tolerances:
        cc.set_statement(
            Tolerances(parsed.tolerances.integration, parsed.tolerances.convergence)
        )

    if parsed.limits:
        lim = parsed.limits
        cc.set_statement(
            Limits(lim.max_iterations, lim.max_warnings, lim.trace_limit)
        )

    # Generic statements (DFQ, WIDTH, SOLVER, etc.)
    _STATEMENT_MAP = {
        "dfq": DFQ,
        "width": Width,
        "list": List,
        "solver": Solver,
        "nan_check": NaNCheck,
        "overwrite_check": OverwriteCheck,
        "time_report": TimeReport,
        "eqsolver": EqSolver,
    }
    for stmt in parsed.statements:
        cls = _STATEMENT_MAP.get(stmt.keyword)
        if cls:
            cc.set_statement(cls(*stmt.args))

    cc.set_statement(End())
    return cc


def _build_components(
    parsed: ParsedDeck,
    dck: Deck,
    proforma_root: Path,
    ctx: DeckContext,
) -> None:
    """Create all TrnsysModel, EquationCollection, ConstantCollection components."""

    # Build TrnsysModel components from UNIT blocks
    for ub in parsed.units:
        _build_unit(ub, dck, proforma_root, ctx)

    # Build equation blocks (standalone, not in user constants)
    for eq_block in parsed.equation_blocks:
        _build_equation_block(eq_block, dck, ctx)

    # Build user constants blocks (equation blocks with studio metadata)
    for uc_block in parsed.user_constants_blocks:
        _build_user_constants_block(uc_block, dck, ctx)


def _build_unit(
    ub: ParsedUnitBlock,
    dck: Deck,
    proforma_root: Path,
    ctx: DeckContext,
) -> None:
    """Build a single TrnsysModel from a ParsedUnitBlock."""
    unit_num = ub.unit.unit_number
    type_num = ub.unit.type_number
    name = ub.unit.name

    # Try to find proforma XML
    xml_path = None
    for studio_m in ub.studio:
        if studio_m.key == "model":
            tmf = Path(studio_m.value.strip().replace("\\", "/"))
            with contextlib.suppress(FileNotFoundError):
                xml_path = _find_proforma(tmf, proforma_root)
            break

    if xml_path is None:
        # Try globbing by type number
        xml_iter = proforma_root.glob(f"Type{type_num}*.xml")
        xml_path = next(iter(xml_iter), None)

    # Create the component
    if xml_path is not None:
        component = TrnsysModel.from_xml(xml_path, name=name, ctx=ctx)
    else:
        component = TrnsysModel(None, name=name, ctx=ctx)

    component._set_unit(unit_num)

    # Apply studio metadata
    _apply_studio(component, ub.studio)

    # Apply parameter values
    if ub.parameters and component._meta and component._meta.variables:
        for i, val in enumerate(ub.parameters.values):
            with contextlib.suppress(ValueError, KeyError, IndexError):
                component.parameters[i] = float(val)

    dck.update_models(component)


def _build_equation_block(
    eq_block: ParsedEquationsBlock,
    dck: Deck,
    ctx: DeckContext,
    studio: tuple[ParsedStudioMarkup, ...] = (),
) -> Component:
    """Build an EquationCollection from a parsed equations block."""
    list_eq = [
        Equation.from_expression(f"{eq.name} = {eq.expression}")
        for eq in eq_block.equations
    ]
    component: Component = EquationCollection(
        list_eq, name=Name("block", registry=ctx.names), ctx=ctx
    )

    # Apply studio metadata (unit_number, position, etc.)
    _apply_studio(component, studio)

    dck.update_models(component)
    return component


def _build_user_constants_block(
    uc_block: ParsedUserConstantsBlock,
    dck: Deck,
    ctx: DeckContext,
) -> None:
    """Build components from a user constants block."""
    if uc_block.equations_block is not None:
        component = _build_equation_block(
            uc_block.equations_block, dck, ctx, studio=uc_block.studio
        )
        # Apply unit number from studio metadata
        for sm in uc_block.studio:
            if sm.key == "unit_number":
                try:
                    old = dck.models.iloc[int(sm.value.strip())]
                    dck.models.pop(old)
                except (KeyError, ValueError):
                    pass
                component._set_unit(int(sm.value.strip()))
                dck.update_models(component)


def _resolve_connections(parsed: ParsedDeck, dck: Deck) -> None:
    """Resolve input connections now that all components exist."""
    from trnsystor.deck import Deck as DeckClass

    for ub in parsed.units:
        if ub.inputs is None:
            continue

        try:
            component = dck.models.loc[ub.unit.unit_number]
        except KeyError:
            continue

        if component._meta is None or not component._meta.variables:
            continue

        # Set input connections
        for i, conn in enumerate(ub.inputs.connections):
            raw = conn.raw
            with contextlib.suppress(KeyError, IndexError, ValueError):
                DeckClass.set_typevariable(dck, i, component, raw, "inputs")

        # Set initial input values
        for i, val in enumerate(ub.inputs.initial_values):
            with contextlib.suppress(KeyError, IndexError, ValueError):
                DeckClass.set_typevariable(
                    dck, i, component, val, "initial_input_values"
                )


def _apply_link_styles(parsed: ParsedDeck, dck: Deck) -> None:
    """Apply link styles from parsed links."""
    for link in parsed.links:
        _apply_one_link(link, dck)


def _apply_one_link(link: ParsedLink, dck: Deck) -> None:
    """Apply a single link style."""
    m = _CONNECTION_SET_RE.match(link.connection_set)
    if not m:
        return

    try:
        u_model = dck.models.iloc[link.u]
        v_model = dck.models.iloc[link.v]
    except KeyError:
        return

    try:
        path_str = m.group("path").strip().split(":")
        mapping = AnchorPoint(u_model).studio_anchor_reverse_mapping

        u_coords = (int(m.group("u1")), int(m.group("u2")))
        v_coords = (int(m.group("v1")), int(m.group("v2")))
        loc = (
            mapping[_find_closest(mapping.keys(), u_coords)],
            mapping[_find_closest(mapping.keys(), v_coords)],
        )
        color = get_rgb_from_int(int(m.group("color")))
        linestyle = _studio_to_linestyle(int(m.group("linestyle")))
        linewidth = int(m.group("linewidth"))

        path = LineString(
            [list(map(int, p.split(","))) for p in path_str]
        )

        u_model.set_link_style(
            v_model,
            loc,
            tuple(c / 256 for c in color),
            linestyle,
            linewidth,
            path,
        )
    except (KeyError, ValueError):
        pass


def _find_proforma(tmf: Path, proforma_root: Path) -> Path:
    """Find a proforma XML file, trying multiple strategies."""
    # Try the exact path first
    if tmf.exists():
        return tmf

    # Try in proforma_root with same name
    xml_basename = tmf.stem + ".xml"
    candidate = proforma_root / xml_basename
    if candidate.exists():
        return candidate

    # Try globbing in proforma_root
    for xml in proforma_root.glob("*.xml"):
        if xml.name == xml_basename:
            return xml

    raise FileNotFoundError(f"Proforma not found: {tmf}")


def _apply_studio(
    component: Component,
    studio: tuple[ParsedStudioMarkup, ...],
) -> None:
    """Apply studio markup to a component."""
    for sm in studio:
        if sm.key == "unit_name":
            component.name = sm.value.strip()
        elif sm.key == "layer":
            component.set_component_layer(sm.value.strip())
        elif sm.key == "position":
            try:
                coords = list(map(float, sm.value.strip().split()))
                component.set_canvas_position(coords, False)
            except (ValueError, TypeError):
                pass
        elif sm.key == "model":
            # Model path is handled during unit construction
            pass
        elif sm.key == "unit_number":
            # Handled by caller for equation blocks
            pass
