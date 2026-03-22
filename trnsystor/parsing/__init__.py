"""Parsing package for TRNSYS .dck files.

This package provides a three-stage pipeline for reading .dck files:

1. **Lexer** (``lexer.tokenize``) — classifies each line into a ``Token``
   with a ``TokenKind`` and captured payload.  O(1) per line via keyword
   dispatch table.

2. **Parser** (``parser.parse``) — consumes the token stream and produces
   a ``ParsedDeck`` tree of frozen dataclasses.  Single-pass state machine.

3. **Resolver** (``resolver.resolve``) — takes a ``ParsedDeck`` and builds
   the domain ``Deck`` by loading XML proformas, creating components, and
   resolving connections.
"""

from trnsystor.parsing.lexer import Token, TokenKind, tokenize
from trnsystor.parsing.parser import DeckParseError, ParsedDeck, parse
from trnsystor.parsing.tokens import SourceLocation

__all__ = [
    "DeckParseError",
    "ParsedDeck",
    "SourceLocation",
    "Token",
    "TokenKind",
    "parse",
    "tokenize",
]
