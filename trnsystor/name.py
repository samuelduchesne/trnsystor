"""Name module."""


class Name(object):
    """Name class.

    Handles the attribution of user defined names for :class:`TrnsysModel`,
    :class:`EquationCollection` and more.
    """

    existing = []  # a list to store the created names

    def __init__(self, name=None):
        """Pick a name. Will increment the name if already used."""
        self.name = self.create_unique(name)

    def create_unique(self, name):
        """Return unique name.

        Checks if ``name`` has already been used. If so, try to increment until not
        used.

        Args:
            name (str): The name to render unique.
        """
        if not name:
            return None
        i = 0
        key = name
        while key in self.existing:
            i += 1
            key = key.split("_")
            key = key[0] + "_{}".format(i)
        the_name = key
        self.existing.append(the_name)
        return the_name

    def __repr__(self):
        """Return str(self)."""
        return str(self)

    def __str__(self):
        """Return str(self)."""
        return str(self.name)
