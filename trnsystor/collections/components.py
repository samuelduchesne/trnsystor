"""ComponentCollection module."""

import collections


class ComponentCollection(collections.UserList):
    """A class that handles collections of components.

    Supported members:
        - :class:`TrnsysModels`
        - :class:`EquationCollections`
        - :class:`ConstantCollections`

    Get a component from a ComponentCollection using either the component's
    unit numer or its full name.

    Examples:
        >>> from trnsystor.collections import ComponentCollection
        >>> cc = ComponentCollection()
        >>> cc.update({tank_type: tank_type})
        >>> cc['Storage Tank; Fixed Inlets, Uniform Losses']._unit = 1
        >>> cc[1]
        Type146: Single Speed Fan/Blower
        >>> cc['Single Speed Fan/Blower']
        Type146: Single Speed Fan/Blower
    """

    @property
    def iloc(self):
        """Access a component by its :attr:`unit_number`."""
        return dict({item.unit_number: item for item in self.data})

    @property
    def loc(self):
        """Access a components by its identify (self).

        Examples:
            >>> cc = ComponentCollection([tank_type])
            >>> assert cc.loc[tank_type] == cc.iloc[tank_type.unit_number]
        """
        return dict({item: item for item in self.data})
