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

    @property
    def inputs(self):
        input_dict = {attr.name: attr for attr in self._meta.variables if
                      isinstance(attr, Input)}
        return InputCollection.from_dict(input_dict)

    @property
    def outputs(self):
        input_dict = {attr.name: attr for attr in self._meta.variables if
                      isinstance(attr, Output)}
        return OutputCollection.from_dict(input_dict)

    @property
    def parameters(self):
        input_dict = {attr.name: attr for attr in self._meta.variables if
                      isinstance(attr, Parameter)}
        return ParameterCollection.from_dict(input_dict)

    def __repr__(self):
        return 'Type{}: {}'.format(self._meta.type, self.name)


class TypeVariables(object):

    def __init__(self, order=None, name=None, role=None, dimension=None,
                 unit=None, type=None, min=None, max=max, boundaries=None,
                 default=None, symbol=None, definition=None):
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

    @classmethod
    def from_tag(cls, **kwargs):
        role = kwargs.pop('role').lower()
        if role == 'parameter':
            return Parameter(**kwargs)
        elif role == 'input':
            return Input(**kwargs)
        elif role == 'output':
            return Output(**kwargs)
        else:
            raise NotImplementedError()

    def __repr__(self):
        return 'VariableName: {}'.format(self.name)

    def _parse_types(self):
        for attr, value in self.__dict__.items():
            if attr in ['default', 'max', 'min']:
                parsed_value = parse(value, self.type, self.unit)
                self.__setattr__(attr, parsed_value)
            if attr in ['order']:
                self.__setattr__(attr, int(value))


def parse(value, _type, unit):
    _type = parse_type(_type)
    _unit = parse_unit(unit)

    if _unit:
        return _type(value) * _unit
    else:
        return _type(value)


ureg = UnitRegistry()


def parse_type(_type):
    if _type == 'integer':
        return int
    elif _type == 'real':
        return float
    else:
        raise NotImplementedError()


def parse_unit(unit):
    if unit == '-':
        return ureg.parse_expression('dimensionless')
    elif unit == '% (base 100)':
        ureg.define('percent = 0.01*count = %')
        return 1 * ureg.percent
    else:
        return ureg.parse_expression(unit)


class Parameter(TypeVariables):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class Input(TypeVariables):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class Output(TypeVariables):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class VariableCollection(object):
    def __init__(self):
        pass

    @classmethod
    def from_dict(cls, dictionary):
        inputs = cls()
        for key in dictionary:
            named_key = re.sub('[^0-9a-zA-Z]+', '_', key)
            inputs.__setattr__(named_key, dictionary[key])
        return inputs


class InputCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass


class OutputCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass


class ParameterCollection(VariableCollection):
    def __init__(self):
        super().__init__()
        pass
