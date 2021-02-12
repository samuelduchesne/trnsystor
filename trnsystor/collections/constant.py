"""ConstantCollection module."""

import collections

import tabulate

from trnsystor.component import Component
from trnsystor.statement import Constant


class ConstantCollection(Component, collections.UserDict):
    """A class that behaves like a dict and collects one or more :class:`Constants`.

    You can pass a dict of Equation or you can pass a list of Equation. In
    the latter, the :attr:`Equation.name` attribute will be used as a key.
    """

    def __init__(self, mutable=None, name=None, **kwargs):
        """Initialize a new ConstantCollection.

        Example:
            >>> c_1 = Constant.from_expression("A = 1")
            >>> c_2 = Constant.from_expression("B = 2")
            >>> ConstantCollection([c_1, c_2])

        Args:
            mutable (Iterable, optional): An iterable.
            name (str): A user defined name for this collection of constants.
                This name will be used to identify this block of constants in
                the .dck file;
        """
        if isinstance(mutable, list):
            _dict = {f.name: f for f in mutable}
        else:
            _dict = mutable
        super(ConstantCollection, self).__init__(_dict, meta=None, name=name, **kwargs)

    def __getitem__(self, key):
        """Get item."""
        if isinstance(key, int):
            value = list(self.data.values())[key]
        elif isinstance(key, slice):
            value = list(self.data.values()).__getitem__(key)
        else:
            value = super().__getitem__(key)
        return value

    def __setitem__(self, key, value):
        """Set item."""
        # optional processing here
        value.model = self
        super().__setitem__(key, value)

    def __repr__(self):
        """Return Deck representation of self."""
        return self._to_deck()

    def __hash__(self):
        """Return hash(self)."""
        return self.unit_number

    def __eq__(self, other):
        """Return self == other."""
        return hash(self) == hash(other)

    def update(self, E=None, **F):
        """Update D from a dict/list/iterable E and F.

        If E is present and has a .keys() method, then does:  for k in E: D[
        k] = E[k]
        If E is present and lacks a .keys() method, then does:  for cts.name,
        cts in E: D[cts.name] = cts
        In either case, this is followed by: for k in F:  D[k] = F[k]

        Args:
            E (list, dict or Constant): The constant to add or update in D (
                self).
            F (list, dict or Constant): Other constants to update are passed.
        """
        if isinstance(E, Constant):
            E.model = self
            _e = {E.name: E}
        elif isinstance(E, list):
            _e = {cts.name: cts for cts in E}
        else:
            for v in E.values():
                if not isinstance(v, Constant):
                    raise TypeError(
                        "Can only update an ConstantCollection with a"
                        "Constant, not a {}".format(type(v))
                    )
            _e = {v.name: v for v in E.values()}
        k: Constant
        for k in F:
            if isinstance(F[k], dict):
                _f = {v.name: v for k, v in F.items()}
            elif isinstance(F[k], list):
                _f = {cts.name: cts for cts in F[k]}
            else:
                raise TypeError(
                    "Can only update an ConstantCollection with a"
                    "Constant, not a {}".format(type(F[k]))
                )
            _e.update(_f)
        super(ConstantCollection, self).update(_e)

    @property
    def size(self) -> int:
        """Return len(self)."""
        return len(self)

    @property
    def unit_number(self) -> int:
        """Return the unit_number of self. Negative by design.

        Hint:
            Only :class:`TrnsysModel` objects have a positive unit_number.
        """
        return self._unit * -1

    def _to_deck(self):
        """Return deck representation of self.

        Examples::

            CONSTANTS n
            NAME1 = ... constant 1 ...
            NAME2 = ... constant 2 ...
            •
            •
            •
            NAMEn = ... constant n ...
        """
        header_comment = '* CONSTANTS "{}"\n\n'.format(self.name)
        head = "CONSTANTS {}\n".format(len(self))
        v_ = ((equa.name, "=", str(equa)) for equa in self.values())
        core = tabulate.tabulate(v_, tablefmt="plain", numalign="left")
        return str(header_comment) + str(head) + str(core)

    def _get_inputs(self):
        """Sort by order number each time it is called."""
        return self

    def _get_outputs(self):
        """Return outputs. Since self is already a  dict, return self."""
        return self
