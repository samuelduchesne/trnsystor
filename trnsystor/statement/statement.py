# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


class Statement(object):
    """This is the base class for many of the TRNSYS Simulation Control and
    Listing Control Statements. It implements common methods such as the repr()
    method.
    """

    def __init__(self):
        self.doc = ""

    def __repr__(self):
        return self._to_deck()

    def _to_deck(self):
        return ""
