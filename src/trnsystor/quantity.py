"""Lightweight Quantity type for unit-aware values.

Replaces pint.Quantity with a minimal implementation that covers the
TRNSYS proforma unit conventions without the overhead of a full
unit-registry.
"""

from __future__ import annotations

import math
import re


# ---------------------------------------------------------------------------
# Conversion factors: source_unit -> {target_unit: factor}
# Q(value, source).to(target) == Q(value * factor, target)
# ---------------------------------------------------------------------------
_CONVERSIONS: dict[str, dict[str, float]] = {
    "l/s": {"m^3/s": 0.001, "m³/s": 0.001},
    "m^3/s": {"l/s": 1000.0, "m³/s": 1.0},
    "m³/s": {"l/s": 1000.0, "m^3/s": 1.0},
    "kg/hr": {"kg/s": 1 / 3600},
    "kg/s": {"kg/hr": 3600.0},
    "kJ/hr": {"W": 1000 / 3600, "kW": 1 / 3600},
    "W": {"kJ/hr": 3600 / 1000},
    "kW": {"kJ/hr": 3600.0},
    "mm": {"m": 0.001, "cm": 0.1},
    "cm": {"m": 0.01, "mm": 10.0},
    "m": {"mm": 1000.0, "cm": 100.0, "km": 0.001},
    "km": {"m": 1000.0},
    "hr": {"s": 3600.0, "min": 60.0},
    "atm": {"Pa": 101325.0, "kPa": 101.325},
    "Wh": {"kJ": 3.6, "J": 3600.0},
    "kJ": {"Wh": 1 / 3.6, "J": 1000.0},
}

# Canonical display names for common units
_DISPLAY: dict[str, str] = {
    "degC": "°C",
    "delta_degC": "Δ°C",
    "percent": "%",
    "dimensionless": "",
    "fraction": "",
    "atm": "atm",
}


_STRIP_PARENS_RE = re.compile(r"\(([^)]+)\)")


def _strip_parens(unit: str) -> str:
    """Strip parentheses from unit components: ``(l)/(s)`` → ``l/s``."""
    return _STRIP_PARENS_RE.sub(r"\1", unit)


class Quantity:
    """A numeric value paired with a unit string.

    Provides the subset of the pint.Quantity API used by trnsystor:
    ``.m`` (magnitude), ``.units``, ``.to(target)``, arithmetic, and
    ``__format__`` with the ``~P`` spec.
    """

    __slots__ = ("_magnitude", "_units")

    def __init__(self, magnitude: float | int, units: str | None = None):
        if isinstance(magnitude, Quantity):
            self._magnitude = float(magnitude._magnitude)
            self._units = magnitude._units if units is None else str(units)
        else:
            self._magnitude = float(magnitude)
            self._units = str(units) if units is not None else "dimensionless"

    # -- pint-compat properties -----------------------------------------

    @property
    def m(self) -> float:
        """Return the magnitude (pint compat)."""
        return self._magnitude

    @property
    def magnitude(self) -> float:
        return self._magnitude

    @property
    def units(self) -> str:
        return self._units

    # -- conversion -----------------------------------------------------

    def to(self, target: str | None) -> Quantity:
        """Convert to *target* units.

        Supports the ~33 unit strings that appear in TRNSYS proformas.
        Raises ``NotImplementedError`` for unknown conversions.
        """
        if target is None or target == self._units:
            return Quantity(self._magnitude, self._units)

        # Normalize parenthesized units: "(l)/(s)" → "l/s"
        src_norm = _strip_parens(self._units)
        tgt_norm = _strip_parens(target)

        if src_norm == tgt_norm:
            return Quantity(self._magnitude, target)

        # Temperature offset conversions
        if src_norm == "degC" and tgt_norm == "K":
            return Quantity(self._magnitude + 273.15, target)
        if src_norm == "K" and tgt_norm == "degC":
            return Quantity(self._magnitude - 273.15, target)

        src = _CONVERSIONS.get(src_norm)
        if src is not None:
            factor = src.get(tgt_norm)
            if factor is not None:
                return Quantity(self._magnitude * factor, target)

        raise NotImplementedError(
            f"Conversion from '{self._units}' to '{target}' is not supported. "
            "Perform manual conversion or open an issue."
        )

    # -- arithmetic -----------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Quantity):
            return (
                math.isclose(self._magnitude, other._magnitude, rel_tol=1e-9)
                and _strip_parens(self._units) == _strip_parens(other._units)
            )
        if isinstance(other, (int, float)):
            return math.isclose(self._magnitude, float(other), rel_tol=1e-9)
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __mul__(self, other: float | int) -> Quantity:
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude * other, self._units)
        return NotImplemented

    def __rmul__(self, other: float | int) -> Quantity:
        return self.__mul__(other)

    def __truediv__(self, other: float | int) -> Quantity:
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude / other, self._units)
        return NotImplemented

    def __add__(self, other: Quantity | float | int) -> Quantity:
        if isinstance(other, Quantity):
            if self._units != other._units:
                raise ValueError(f"Cannot add '{self._units}' and '{other._units}'")
            return Quantity(self._magnitude + other._magnitude, self._units)
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude + other, self._units)
        return NotImplemented

    def __sub__(self, other: Quantity | float | int) -> Quantity:
        if isinstance(other, Quantity):
            if self._units != other._units:
                raise ValueError(
                    f"Cannot subtract '{other._units}' from '{self._units}'"
                )
            return Quantity(self._magnitude - other._magnitude, self._units)
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude - other, self._units)
        return NotImplemented

    def __lt__(self, other: Quantity | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._magnitude < other._magnitude
        return self._magnitude < float(other)

    def __le__(self, other: Quantity | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._magnitude <= other._magnitude
        return self._magnitude <= float(other)

    def __gt__(self, other: Quantity | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._magnitude > other._magnitude
        return self._magnitude > float(other)

    def __ge__(self, other: Quantity | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._magnitude >= other._magnitude
        return self._magnitude >= float(other)

    def __float__(self) -> float:
        return self._magnitude

    def __int__(self) -> int:
        return int(self._magnitude)

    def __hash__(self) -> int:
        return hash((self._magnitude, self._units))

    # -- display --------------------------------------------------------

    def _display_units(self) -> str:
        normalized = _strip_parens(self._units)
        return _DISPLAY.get(normalized, normalized)

    def __repr__(self) -> str:
        disp = self._display_units()
        mag = self._magnitude
        # Show integers without decimal point for pint compat
        mag_str = str(int(mag)) if mag == int(mag) else str(mag)
        if disp:
            return f"{mag_str} {disp}"
        return mag_str

    def __str__(self) -> str:
        return self.__repr__()

    def __format__(self, spec: str) -> str:
        # Support the ``~P`` (pretty) format spec used by pint
        if "~P" in spec or "~p" in spec:
            disp = self._display_units()
            mag = self._magnitude
            mag_str = str(int(mag)) if mag == int(mag) else str(mag)
            return f"{mag_str} {disp}".rstrip()
        # Fall back to formatting the magnitude
        if spec:
            return format(self._magnitude, spec)
        return str(self)
