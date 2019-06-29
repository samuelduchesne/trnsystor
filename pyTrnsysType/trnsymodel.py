import collections
import copy
import math
import re

from bs4 import BeautifulSoup, Tag
from pint import UnitRegistry
from pint.quantity import _Quantity


class ArrayOfTrnsysType(object):
    def __init__(self):
        self.objs = None


class MetaData(object):

    def __init__(self, object=None, author=None, organization=None, editor=None,
                 creationDate=None, modifictionDate=None, mode=None,
                 validation=None, icon=None, type=None, maxInstance=None,
                 keywords=None, details=None, comment=None, variables=None,
                 variablesComment=None, cycles=None, source=None, **kwargs):
        self.object = object
        self.author = author
        self.organization = organization
        self.editor = editor
        self.creationDate = creationDate
        self.modifictionDate = modifictionDate
        self.mode = mode
        self.validation = validation
        self.icon = icon
        self.type = type
        self.maxInstance = maxInstance
        self.keywords = keywords
        self.details = details
        self.comment = comment
        self.variablesComment = variablesComment
        self.cycles = cycles
        self.source = source

        self.variables = variables

    @classmethod
    def from_tag(cls, **kwargs):
        return cls(**{attr: kwargs[attr].text for attr in kwargs})


class TrnsysModel(object):

    def __init__(self, meta, name):
        """

        Args:
            name (str):
            meta (MetaData):
        """
        self._meta = meta
        self.name = name

        # self.get_inputs()
        # self.get_outputs()
        # self.get_parameters()

    @classmethod
    def from_xml(cls, xml):
        all_types = []
        soup = BeautifulSoup(xml, 'xml')
        my_objects = soup.findAll("TrnsysModel")
        for trnsystype in my_objects:
            t = TrnsysModel.from_tag(
                **{child.name: child for child in trnsystype.children
                   if isinstance(child, Tag)})
            all_types.append(t)
        if len(all_types) > 1:
            return all_types
        else:
            return all_types[0]

    @classmethod
    def from_tag(cls, **kwargs):
        meta = MetaData.from_tag(**kwargs)
        name = kwargs.get('object').text
        model = TrnsysModel(meta, name)
        type_vars = [TypeVariables.from_tag(tag)
                     for tag in kwargs['variables']
                     if isinstance(tag, Tag)]
        type_cycles = CycleCollection(TypeCycle.from_tag(tag)
                                      for tag in kwargs.get('cycles').children
                                      if isinstance(tag, Tag))
        model._meta.variables = type_vars
        model._meta.cycles = type_cycles

        model.trigger_variables()

        return model

    def trigger_variables(self):
        self.get_inputs()
        self.get_outputs()
        self.get_parameters()

    def get_inputs(self):
        input_dict = collections.OrderedDict(
            (attr.name, attr) for attr in
            sorted(filter(lambda x: isinstance(x, Input),
                          self._meta.variables),
                   key=lambda key: key.order)
        )
        self.resolve_cycles(input_dict, 'input')
        self.inputs = InputCollection.from_dict(input_dict)

    def get_outputs(self):
        output_dict = collections.OrderedDict(
            (id(attr), attr) for attr in
            sorted(filter(lambda o: isinstance(o, Output),
                          self._meta.variables),
                   key=lambda key: key.order)
        )
        self.resolve_cycles(output_dict, 'output')
        self.outputs = OutputCollection.from_dict(output_dict)

    def get_parameters(self):
        param_dict = collections.OrderedDict(
            (id(attr), attr) for attr in
            sorted(filter(lambda o: isinstance(o, Parameter),
                          self._meta.variables),
                   key=lambda key: key.order)
        )
        self.resolve_cycles(param_dict, 'parameter')
        self.parameters = ParameterCollection.from_dict(param_dict)

    def resolve_cycles(self, output_dict, type_):
        cycles = {str(id(attr)): attr for attr in self._meta.cycles if
                  attr.role == type_}
        # repeat cycle variables n times
        for _, cycle in cycles.items():
            idxs = [(int(cycle.firstRow) - 1)
                    for cycle in cycle.cycles]
            items = [output_dict.pop(id(key))
                     for key in [list(output_dict.values())[i] for i in idxs]]
            n_times = [list(
                filter(lambda o: o.name == cycle.paramName,
                       self._meta.variables)
            )[0].value.m for cycle in cycle.cycles]
            for item, n_time in zip(items, n_times):
                basename = item.name
                for n, _ in enumerate(range(n_time), start=1):
                    item = item.copy()
                    item.name = basename + "-{}".format(n)
                    item.order += len(idxs)  # so that oder number is unique
                    output_dict.update({id(item): item})

    def __repr__(self):
        return 'Type{}: {}'.format(self._meta.type, self.name)


class TypeVariables(object):

    def __init__(self, val, order=None, name=None, role=None, dimension=None,
                 unit=None, type=None, min=None, max=max, boundaries=None,
                 default=None, symbol=None, definition=None):
        super().__init__()
        self.order = order
        self.name = name
        self.role = role
        self.dimension = dimension
        self.unit = unit
        self.type = type
        self.min = min
        self.max = max
        self.boundaries = boundaries
        self.default = default
        self.symbol = symbol
        self.definition = definition
        self.value = parse_value(val, self.type, self.unit,
                                 (self.min, self.max))

    @classmethod
    def from_tag(cls, tag):

        role = tag.find('role').text
        val = tag.find('default').text
        _type = parse_type(tag.find('type').text)
        attr = {attr.name: attr.text for attr in tag if isinstance(attr, Tag)}
        if role == 'parameter':
            return Parameter(_type(val), **attr)
        elif role == 'input':
            return Input(_type(val), **attr)
        elif role == 'output':
            return Output(_type(val), **attr)
        else:
            raise NotImplementedError()

    def __float__(self):
        return self.value.m

    def __str__(self):
        return '{} = {}'.format(self.name, self.value)

    def __repr__(self):
        return '{}'.format(self.value)

    def copy(self):
        new_self = copy.copy(self)
        return new_self

    def _parse_types(self):
        for attr, value in self.__dict__.items():
            if attr in ['default', 'max', 'min']:
                parsed_value = parse_value(value, self.type, self.unit,
                                           (self.min, self.max))
                self.__setattr__(attr, parsed_value)
            if attr in ['order']:
                self.__setattr__(attr, int(value))


class TypeCycle(object):
    def __init__(self, role=None, firstRow=None, lastRow=None, cycles=None,
                 minSize=None, maxSize=None, paramName=None,
                 **kwargs):
        super().__init__()
        self.role = role
        self.firstRow = firstRow
        self.lastRow = lastRow
        self.cycles = cycles
        self.minSize = minSize
        self.maxSize = maxSize
        self.paramName = paramName

    @classmethod
    def from_tag(cls, tag_):
        dict_ = collections.defaultdict(list)
        for attr in filter(lambda x: isinstance(x, Tag), tag_):
            if attr.name != 'cycles' and not attr.is_empty_element:
                dict_[attr.name] = attr.text
            elif attr.is_empty_element:
                pass
            else:
                dict_['cycles'].extend([cls.from_tag(tag) for tag in attr
                                        if isinstance(tag, Tag)])
        return cls(**dict_)

    def __repr__(self):
        return self.role + " {} to {}".format(self.firstRow, self.lastRow)


class CycleCollection(collections.UserList):
    def __getitem__(self, key):
        value = super().__getitem__(key)
        return value


ureg = UnitRegistry()


def resolve_type(args):
    if isinstance(args, _Quantity):
        return args.m
    else:
        return float(args)


def parse_value(value, _type, unit, bounds=(-math.inf, math.inf)):
    _type = parse_type(_type)
    Q_, unit_ = parse_unit(unit)

    f = _type(value)
    xmin, xmax = map(resolve_type, bounds)
    is_bound = xmin <= f <= xmax
    if is_bound:
        if unit_:
            return Q_(f, unit_)
        else:
            return f
    else:
        # out of bounds
        msg = 'Value is out of bounds. ' \
              '{xmin} <= {value} <= {xmax}'.format(
            xmin=xmin, value=f, xmax=xmax
        )
        raise ValueError(msg)


def parse_type(_type):
    if _type == 'integer':
        return int
    elif _type == 'real':
        return float
    else:
        raise NotImplementedError()


def parse_unit(unit):
    Q_ = ureg.Quantity
    if unit == '-':
        return Q_, ureg.parse_expression('dimensionless')
    elif unit == '% (base 100)':
        ureg.define('percent = 0.01*count = %')
        return Q_, ureg.percent
    elif unit.lower() == 'c':
        Q_ = ureg.Quantity
        return Q_, ureg.degC
    elif unit.lower() == 'deltac':
        Q_ = ureg.Quantity
        return Q_, ureg.delta_degC
    else:
        return Q_, ureg.parse_expression(unit)


class Parameter(TypeVariables):
    def __init__(self, val, **kwargs):
        super().__init__(val, **kwargs)

        self._parse_types()


class Input(TypeVariables):
    def __init__(self, val, **kwargs):
        super().__init__(val, **kwargs)

        self._parse_types()


class Output(TypeVariables):
    def __init__(self, val, **kwargs):
        super().__init__(val, **kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class VariableCollection(collections.UserDict):

    def __getitem__(self, key):
        value = super(VariableCollection, self).__getitem__(key)
        return value.value

    def __setitem__(self, key, value):
        # todo: implement trigger recycle here
        if isinstance(value, TypeVariables):
            """if a TypeVariable is given, simply set it"""
            super().__setitem__(key, value)
        elif isinstance(value, (int, float)):
            """a str, float, int, etc. is passed"""
            value = parse_value(value, self.data[key].type, self.data[key].unit,
                                (self.data[key].min, self.data[key].max))
            self.data[key].__setattr__('value', value)
        else:
            raise TypeError('Cannot set a value of type {} in this '
                            'VariableCollection')

    @classmethod
    def from_dict(cls, dictionary):
        item = cls()
        for key in dictionary:
            named_key = re.sub('[^0-9a-zA-Z]+', '_', dictionary[key].name)
            item.__setitem__(named_key, dictionary[key])
        return item

    @property
    def size(self):
        return len(self)

    def trigger_variables(self):
        pass


class InputCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = '{} Inputs:\n'.format(self.size)
        inputs = '\n'.join(['"{}": {}'.format(key, value.value)
                            for key, value in self.data.items()])
        return num_inputs + inputs


class OutputCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = '{} Outputs:\n'.format(self.size)
        inputs = '\n'.join(['"{}": {}'.format(key, value.value)
                            for key, value in self.data.items()])
        return num_inputs + inputs


class ParameterCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = '{} Parameters:\n'.format(self.size)
        inputs = '\n'.join(['"{}": {}'.format(key, value.value)
                            for key, value in self.data.items()])
        return num_inputs + inputs
