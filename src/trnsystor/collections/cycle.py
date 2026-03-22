"""CycleCollection module."""

import collections


class CycleCollection(collections.UserList):
    """Collection of :class:`trnsystor.typecycle.TypeCycle`."""

    def __getitem__(self, key):
        """Get item by key."""
        value = super().__getitem__(key)
        return value
