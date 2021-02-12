"""Statement module."""


class Statement(object):
    """Statement class.

    This is the base class for many of the TRNSYS Simulation Control and
    Listing Control Statements. It implements common methods such as the repr()
    method.
    """

    def __init__(self):
        """Initialize object."""
        self.doc = ""

    def __repr__(self):
        """Return deck representation of self."""
        return self._to_deck()

    def _to_deck(self):
        """Return deck representation of self."""
        return ""
