import collections
import copy
import itertools
import math
import re

from bs4 import BeautifulSoup, Tag
from pint import UnitRegistry
from pint.quantity import _Quantity

import pyTrnsysType


class MetaData(object):

    def __init__(self, object=None, author=None, organization=None, editor=None,
                 creationDate=None, modifictionDate=None, mode=None,
                 validation=None, icon=None, type=None, maxInstance=None,
                 keywords=None, details=None, comment=None, variables=None,
                 plugin=None, variablesComment=None, cycles=None, source=None,
                 **kwargs):
        """General information that associated with a TrnsysModel. This
        information is contained in the General Tab of the Proforma.

        Args:
            object (str): A generic name describing the component model.
            author (str): The name of the person who wrote the model.
            organization (str): The name of organization with which the Author
                is affiliated.
            editor (str): Often, the person creating the Simulation Studio
                Proforma is not the original author and so the name of the
                Editor may also be important.
            creationDate (str): This is the date of when the model was first
                written.
            modifictionDate (str): This is the date when the Proforma was mostly
                recently revised.
            mode (int): 1-Detailed, 2-Simplified, 3-Empirical, 4- Conventional
                validation (int): Determine the type of validation that was
                performed on this model. This can be 1-qualitative, 2-numerical,
                3-analytical, 4-experimental and 5-‘in assembly’ meaning that it
                was verified as part of a larger system which was verified.
            validation:
            icon (Path): Path to the icon.
            type (int): The type number.
            maxInstance (int): The maximum number of instances this type can be
                used.
            keywords (str): keywords associated with this model.
            details (str): The detailed description contains an explanation of
                the model including a mathematical description of the model
            comment (str): The text entered here will appear as a comment in the
                TRNSYS input file. This allows to attach important information
                about the component to all its users, including users who prefer
                to edit the input file with a text editor. This text should be
                short, to avoid overloading the input file.
            variables (list, optional): a list of :class:`TypeVariable`.
            plugin (Path): The plug-in path contains the path to the an external
                application which will be executed to modify component
                properties instead of the classical properties window.
            variablesComment (str): #todo What is this?
            cycles (list, optional): List of TypeCycle.
            source (Path): Path of the source code.
            **kwargs:
        """
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
        self.plugin = plugin
        self.cycles = cycles
        self.source = source

        self.variables = variables

        self.check_extra_tags(kwargs)

    @classmethod
    def from_tag(cls, tag):
        """Class mothod used to create a TrnsysModel from a xml Tag

        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        kwargs = {child.name: child for child in tag.children
                  if isinstance(child, Tag)}
        return cls(**{attr: kwargs[attr].text for attr in kwargs})

    def check_extra_tags(self, kwargs):
        """Detect extra tags in the proforma and warn.

        Args:
            kwargs:
        """
        if kwargs:
            msg = 'Unknown tags have been detected in this proforma: {}.\nIf ' \
                  'you wish to continue, the behavior of the object might be ' \
                  'affected. Please contact the package developers or submit ' \
                  'an issue.\n Do you wish to continue anyways?'.format(
                ', '.join(kwargs.keys()))
            shall = input("%s (y/N) " % msg).lower() == 'y'
            if not shall:
                raise NotImplementedError()


class ExternalFile(object):

    def __init__(self):
        pass


class TrnsysModel(object):
    new_id = itertools.count(start=1)

    # todo: check what are the legal unit numbers

    def __init__(self, meta, name):
        """
        Todo:
            - Create to_deck functionality

        Args:
            meta (MetaData):
            name (str):
        """
        self._unit = next(self.new_id)
        self._meta = meta
        self.name = name

    @classmethod
    def from_xml(cls, xml):
        """Class method to create a :class:`TrnsysModel` from an xml string.
        :param xml:

        Examples:
            First open the xml file and read it.

            >>> from pyTrnsysType import TrnsysModel
            >>> with open("Tests/input_files/Type146.xml") as xml:
            ...    fan1 = TrnsysModel.from_xml(xml.read())

        Args:
            xml (str): The string representation of an xml file
        """
        all_types = []
        soup = BeautifulSoup(xml, 'xml')
        my_objects = soup.findAll("TrnsysModel")
        for trnsystype in my_objects:
            t = cls._from_tag(trnsystype)
            all_types.append(t)
        if len(all_types) > 1:
            return all_types
        else:
            return all_types[0]

    @classmethod
    def _from_tag(cls, tag):
        """Class method to create a :class:`TrnsysModel` from a tag

        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        meta = MetaData.from_tag(tag)
        name = tag.find('object').text

        model = TrnsysModel(meta, name)
        type_vars = [TypeVariable.from_tag(tag)
                     for tag in tag.find('variables')
                     if isinstance(tag, Tag)]
        type_cycles = CycleCollection(TypeCycle.from_tag(tag)
                                      for tag in tag.find('cycles').children
                                      if isinstance(tag, Tag))
        model._meta.variables = type_vars
        model._meta.cycles = type_cycles

        return model

    @property
    def inputs(self):
        return self.get_inputs()

    @property
    def outputs(self):
        return self.get_outputs()

    @property
    def parameters(self):
        return self.get_parameters()

    @property
    def unit_number(self):
        return int(self._unit)

    @property
    def type_number(self):
        return int(self._meta.type)

    def get_inputs(self):
        """inputs getter. Sorts by order number and resolves cycles each time it
        is called
        """
        input_dict = collections.OrderedDict(
            (attr.name, attr) for attr in
            sorted(filter(lambda x: isinstance(x, Input),
                          self._meta.variables),
                   key=lambda key: key.order)
        )
        self.resolve_cycles(input_dict, 'input')
        return InputCollection.from_dict(input_dict)

    def get_outputs(self):
        """outputs getter. Sorts by order number and resolves cycles each time
        it is called
        """
        output_dict = collections.OrderedDict(
            (id(attr), attr) for attr in
            sorted(filter(lambda o: isinstance(o, Output),
                          self._meta.variables),
                   key=lambda key: key.order)
        )
        self.resolve_cycles(output_dict, 'output')
        return OutputCollection.from_dict(output_dict)

    def get_parameters(self):
        """parameters getter. Sorts by order number and resolves cycles each
        time it is called
        """
        param_dict = collections.OrderedDict(
            (id(attr), attr) for attr in
            sorted(filter(lambda o: isinstance(o, Parameter),
                          self._meta.variables),
                   key=lambda key: key.order)
        )
        self.resolve_cycles(param_dict, 'parameter')
        return ParameterCollection.from_dict(param_dict)

    def resolve_cycles(self, output_dict, type_):
        """Cycle resolver. Proformas can contain parameters, inputs and ouputs
        that have a variable number of entries. This will deal with their
        creation each time the linked parameters are changed.

        Args:
            output_dict (dict): A dictionary of :class:`TypeVariable`.
            type_:
        """
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
        return 'Type{}: {}'.format(self.type_number, self.name)

    def to_deck(self):
        """print the Input File (.dck) representation of this TrnsysModel"""
        input = pyTrnsysType.UnitType(self.unit_number, self.type_number,
                                      self.name)
        params = pyTrnsysType.Parameters(self.parameters,
                                         n=self.parameters.size)
        inputs = pyTrnsysType.Inputs(self.inputs, n=self.inputs.size)

        return str(input) + str(params) + str(inputs)


class TypeVariable(object):

    def __init__(self, val, order=None, name=None, role=None, dimension=None,
                 unit=None, type=None, min=None, max=max, boundaries=None,
                 default=None, symbol=None, definition=None):
        """Class containing a proforma variable.

        Args:
            val (int, float or pint._Quantity): The actual value holded by this
                object.
            order (str):
            name (str): This name will be seen by the user in the connections
                window and all other variable information windows.
            role (str): The role of the variables such as input, output, etc.
                Changing the role of a standard component requires reprogramming
                and recompiling the component.
            dimension (str): The dimension of the variable (power, temperature,
                etc.): This dimension must be already defined in the unit
                dictionary (refer to section 2.9) to be used. The pre-defined
                dimension ‘any’ allows to make a variable compatible with any
                other variable: no checks are performed on such variables if the
                user attempts to connect them to other variables.
            unit (type): The unit of the variable that the TRNSYS program
                requires for the specified dimension (C, F, K etc.)
            type (str): The type of the variable: Real, integer, Boolean, or
                string.
            min (int, float or pint._Quantity): The minimum value. The minimum
                and maximum can be "-INF" or "+INF" to indicate no limit
                (infinity). +/-INF is the default value.
            max (int, float or pint._Quantity): The maximum value. The minimum
                and maximum can be "-INF" or "+INF" to indicate no limit
                (infinity). +/-INF is the default value.
            boundaries (str): This setting determines if the minimum and maximum
                are included or not in the range. choices are "[;]", "[;[",
                "];]" ,"];["
            default (int, float or pint._Quantity): the default value of the
                variable. The default value is replaced by the initial value for
                the inputs and derivatives and suppressed for the outputs
            symbol (str): The symbol of the unit (not used).
            definition (str): A short description of the variable.
        """
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
                                 (self.min, self.max), self.name)

    @classmethod
    def from_tag(cls, tag):
        """Class method to create a TypeVariable from an XML tag.

        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        role = tag.find('role').text
        val = tag.find('default').text
        _type = parse_type(tag.find('type').text)
        attr = {attr.name: attr.text for attr in tag if isinstance(attr, Tag)}
        if role == 'parameter':
            return Parameter(_type(float(val)), **attr)
        elif role == 'input':
            return Input(_type(float(val)), **attr)
        elif role == 'output':
            return Output(_type(float(val)), **attr)
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
                parsed_value = parse_value(value, self.type, self.unit,
                                           (self.min, self.max))
                self.__setattr__(attr, parsed_value)
            if attr in ['order']:
                self.__setattr__(attr, int(value))

    def copy(self):
        """make a copy of the object"""
        new_self = copy.copy(self)
        return new_self


class TypeCycle(object):
    def __init__(self, role=None, firstRow=None, lastRow=None, cycles=None,
                 minSize=None, maxSize=None, paramName=None,
                 **kwargs):
        """
        Args:
            role:
            firstRow:
            lastRow:
            cycles:
            minSize:
            maxSize:
            paramName:
            **kwargs:
        """
        super().__init__()
        self.role = role
        self.firstRow = firstRow
        self.lastRow = lastRow
        self.cycles = cycles
        self.minSize = minSize
        self.maxSize = maxSize
        self.paramName = paramName

    @classmethod
    def from_tag(cls, tag):
        """
        Args:
            tag (Tag): The XML tag with its attributes and contents.
        """
        dict_ = collections.defaultdict(list)
        for attr in filter(lambda x: isinstance(x, Tag), tag):
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
        """
        Args:
            key:
        """
        value = super().__getitem__(key)
        return value


ureg = UnitRegistry()


def resolve_type(args):
    """
    Args:
        args:
    """
    if isinstance(args, _Quantity):
        return args.m
    else:
        return float(args)


def parse_value(value, _type, unit, bounds=(-math.inf, math.inf), name=None):
    """
    Args:
        value:
        _type:
        unit:
        bounds:
        name:
    """
    if not name:
        name = ''
    _type = parse_type(_type)
    Q_, unit_ = parse_unit(unit)

    try:
        f = _type(value)
    except:
        f = float(value)
    xmin, xmax = map(resolve_type, bounds)
    is_bound = xmin <= f <= xmax
    if is_bound:
        if unit_:
            return Q_(f, unit_)
    else:
        # out of bounds
        msg = 'Value {} "{}" is out of bounds. ' \
              '{xmin} <= value <= {xmax}'.format(name, f, xmin=Q_(xmin, unit_),
                                                 xmax=Q_(xmax, unit_))
        raise ValueError(msg)


def parse_type(_type):
    """
    Args:
        _type:
    """
    if _type == 'integer':
        return int
    elif _type == 'real':
        return float
    else:
        raise NotImplementedError()


def parse_unit(unit):
    """
    Args:
        unit:
    """
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


class Parameter(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to parameters"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to parameters.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class Input(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to inputs"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to inputs.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class Output(TypeVariable):
    """A subclass of :class:`TypeVariable` specific to outputs"""

    def __init__(self, val, **kwargs):
        """A subclass of :class:`TypeVariable` specific to outputs.

        Args:
            val:
            **kwargs:
        """
        super().__init__(val, **kwargs)

        self._parse_types()

    def __repr__(self):
        return '{}'.format(self.name)


class VariableCollection(collections.UserDict):
    """A collection of :class:`VariableType` as a dict. Handles getting and
    setting variable values."""

    def __getitem__(self, key):
        """
        Args:
            key:
        """
        value = super(VariableCollection, self).__getitem__(key)
        return value.value

    def __setitem__(self, key, value):
        """
        Args:
            key:
            value:
        """
        if isinstance(value, TypeVariable):
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
        """

        Args:
            dictionary:
        """
        item = cls()
        for key in dictionary:
            named_key = re.sub('[^0-9a-zA-Z]+', '_', dictionary[key].name)
            item.__setitem__(named_key, dictionary[key])
        return item

    @property
    def size(self):
        """The number of parameters"""
        return len(self)

    def trigger_variables(self):
        pass


class InputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Inputs"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = '{} Inputs:\n'.format(self.size)
        inputs = '\n'.join(['"{}": {}'.format(key, value.value)
                            for key, value in self.data.items()])
        return num_inputs + inputs


class OutputCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Ouputs"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = '{} Outputs:\n'.format(self.size)
        inputs = '\n'.join(['"{}": {}'.format(key, value.value)
                            for key, value in self.data.items()])
        return num_inputs + inputs


class ParameterCollection(VariableCollection):
    """Subclass of :class:`VariableCollection` specific to Parameters"""

    def __init__(self):
        super().__init__()
        pass

    def __repr__(self):
        num_inputs = '{} Parameters:\n'.format(self.size)
        inputs = '\n'.join(['"{}": {}'.format(key, value.value)
                            for key, value in self.data.items()])
        return num_inputs + inputs
