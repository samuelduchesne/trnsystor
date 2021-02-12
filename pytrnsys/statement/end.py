# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and pytrnsys contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from pytrnsys.statement.statement import Statement


class End(Statement):
    """The END statement must be the last line of a TRNSYS input file. It
    signals the TRNSYS processor that no more control statements follow and that
    the simulation may begin.
    """

    def __init__(self):
        super().__init__()
        self.doc = "The END Statement"

    def _to_deck(self):
        return "END"