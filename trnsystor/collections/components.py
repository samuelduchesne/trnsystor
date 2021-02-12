# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (c) 2019 - 2021. Samuel Letellier-Duchesne and trnsystor contributors  +
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import collections


class ComponentCollection(collections.UserList):
    """A class that handles collections of components, eg.; TrnsysModels,
    EquationCollections and ConstantCollections

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
        return dict({item.unit_number: item for item in self.data})

    @property
    def loc(self):
        return dict({item: item for item in self.data})
