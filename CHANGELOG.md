# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.0] - 2026-10-25

### Added

- `symbolic` optional extra (`pip install trnsystor[symbolic]`) for equation parsing with sympy.
- `viz` optional extra (`pip install trnsystor[viz]`) for plotting with matplotlib.
- `step` argument on `StudioCanvas` to set the routing grid resolution.

### Changed

- **Breaking:** quantities are now `trnsystor.quantity.Quantity` objects instead of `pint.Quantity`. Whole numbers display without a decimal (`20` instead of `20.0`).
- **Breaking:** sympy is no longer installed by default. Install the `symbolic` extra to parse equations into sympy expressions.
- **Breaking:** matplotlib, numpy and pandas are no longer core dependencies. Install the `viz` extra for plotting.
- **Breaking:** requires Python 3.10 or newer.
- **Breaking:** file paths are `pathlib.Path` objects instead of `path.Path`.
- Parsing state now lives in a per-deck `DeckContext` instead of class-level globals, so reading several decks in the same process no longer leaks unit numbers, names or constants between them.
- Deck parsing is split into separate lexer, parser and serialization layers and is faster on large decks.
- Library code no longer prompts with `input()`; it logs warnings instead.
- Link routing on the Studio canvas computes paths on demand instead of building the full grid up front.

### Removed

- **Breaking:** dependencies on `pint`, `path`, `pandas`, `numpy` and `outdated`.

### Fixed

- The bottom-right anchor point on components was mirrored to the bottom-left.
- Saving a deck that contains equations failed when sympy was not installed.

### Security

- Development lockfile now resolves Pillow 13.0.0 on Python 3.11+, fixing GHSA-58r4-6rv3-gfh8 (out-of-bounds access in `_imagingmorph`) and other Pillow advisories. Pillow is not a runtime dependency of trnsystor.

[unreleased]: https://github.com/samuelduchesne/trnsystor/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/samuelduchesne/trnsystor/compare/v1.4.1...v1.5.0
