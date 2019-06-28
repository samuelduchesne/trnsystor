import collections
import re

from bs4 import BeautifulSoup, Tag
from pint import UnitRegistry


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


class TrnsysModel(object):

    def __init__(self, meta, name):
        self._meta = meta
        self.name = name

        self.get_inputs()
        self.get_outputs()
        self.get_parameters()

    @classmethod
    def from_xml(cls, xml):
        all_types = []
        soup = BeautifulSoup(xml, 'xml')
        my_objects = soup.findAll("TrnsysModel")
        for trnsystype in my_objects:
            t = TrnsysModel.from_tag(
                **{child.name: child.text for child in trnsystype.children
                   if
                   isinstance(child, Tag)})
            vars = trnsystype.find("variables")
            all_types.append(t)
            t._meta.variables = []
            for var in vars:
                if not isinstance(var, Tag):
                    pass
                else:
                    v = TypeVariables.from_tag(
                        **{child.name: child.text for child in var.children
                           if
                           isinstance(child, Tag)})
                    t._meta.variables.append(v)
            t.get_inputs()
            t.get_outputs()
            t.get_parameters()
        if len(all_types) > 1:
            return all_types
        else:
            return all_types[0]

    @classmethod
    def from_tag(cls, **kwargs):
        meta = MetaData(**kwargs)
        name = kwargs.get('object')
        model = TrnsysModel(meta, name)
        return model

    def get_inputs(self):
        input_dict = {attr.name: attr for attr in self._meta.variables if
                      isinstance(attr, Input)}
        self.inputs = InputCollection.from_dict(input_dict)

    def get_outputs(self):
        input_dict = {attr.name: attr for attr in self._meta.variables if
                      isinstance(attr, Output)}
        self.outputs = OutputCollection.from_dict(input_dict)

    def get_parameters(self):
        input_dict = {attr.name: attr for attr in self._meta.variables if
                      isinstance(attr, Parameter)}
        self.parameters = ParameterCollection.from_dict(input_dict)

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
        self.value = parse(val, self.type, self.unit)

    @classmethod
    def from_tag(cls, **kwargs):
        role = kwargs.pop('role').lower()
        val = kwargs.get('default')
        _type = parse_type(kwargs.get('type'))
        if role == 'parameter':
            return Parameter(_type(val), **kwargs)
        elif role == 'input':
            return Input(_type(val), **kwargs)
        elif role == 'output':
            return Output(_type(val), **kwargs)
        else:
            raise NotImplementedError()

    def __float__(self):
        return self.value.m

    def __str__(self):
        return '{} = {}'.format(self.name, self.value)

    def __repr__(self):
        return '{}'.format(self.value)

    def _parse_types(self):
        for attr, value in self.__dict__.items():
            if attr in ['default', 'max', 'min']:
                parsed_value = parse(value, self.type, self.unit)
                self.__setattr__(attr, parsed_value)
            if attr in ['order']:
                self.__setattr__(attr, int(value))


ureg = UnitRegistry()


def parse(value, _type, unit):
    _type = parse_type(_type)
    Q_, unit_ = parse_unit(unit)

    if unit_:
        return Q_(_type(value), unit_)
    else:
        return _type(value)


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
        # todo: implement value boundaries logic here
        if isinstance(value, TypeVariables):
            super().__setitem__(key, value)
        else:
            value = parse(value, self.data[key].type, self.data[key].unit)
            self.data[key].__setattr__('value', value)

    @classmethod
    def from_dict(cls, dictionary):
        item = cls()
        for key in dictionary:
            named_key = re.sub('[^0-9a-zA-Z]+', '_', key)
            item.__setitem__(named_key, dictionary[key])
        return item

    @property
    def size(self):
        return len(self)


class InputCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        return '{} Inputs'.format(self.size)


class OutputCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        return '{} Outputs'.format(self.size)


class ParameterCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        return '{} Parameters'.format(self.size)
