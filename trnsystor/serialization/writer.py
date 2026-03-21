"""Top-level Deck serializer."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trnsystor.deck import Deck


def serialize_deck(obj: Deck) -> str:
    """Return deck string representation of a Deck object."""
    from trnsystor.statement import End

    end = obj.control_cards.__dict__.pop("end", End())
    cc = str(obj.control_cards)

    models = "\n\n".join([model._to_deck() for model in obj.models])

    styles = (
        "\n*!LINK_STYLE\n"
        + "".join(
            map(
                str,
                list(
                    itertools.chain.from_iterable(
                        [
                            model.studio.link_styles.values()
                            for model in obj.models
                        ]
                    )
                ),
            )
        )
        + "*!LINK_STYLE_END"
    )

    end_str = end._to_deck()
    return "\n".join([cc, models, end_str]) + styles
