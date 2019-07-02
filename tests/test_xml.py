import pytest
from mock import patch


@pytest.fixture()
def fan_type():
    """Fixture to create a TrnsysModel from xml"""
    from pyTrnsysType import TrnsysModel
    with open("tests/input_files/Type146.xml") as xml:
        fan1 = TrnsysModel.from_xml(xml.read())
    yield fan1


@pytest.fixture()
def pipe_type():
    """Fixture to create a TrnsysModel from xml"""
    from pyTrnsysType import TrnsysModel
    with open("tests/input_files/Type951.xml") as xml:
        fan1 = TrnsysModel.from_xml(xml.read())
    yield fan1


@pytest.fixture()
def tank_type():
    from pyTrnsysType import TrnsysModel
    with patch('builtins.input', return_value='y'):
        with open("tests/input_files/Type4a.xml") as xml:
            tank = TrnsysModel.from_xml(xml.read())
        yield tank


@patch('builtins.input', return_value='y')
def test_chiller_type(input):
    """Fixture to create a TrnsysModel from xml from an xml that contains
    unknown tags. Should primpt user. Passes when input == 'y'"""
    from pyTrnsysType import TrnsysModel
    with open("tests/input_files/Type107-simplified.xml") as xml:
        fan1 = TrnsysModel.from_xml(xml.read())
    return fan1


def test_cycles(pipe_type):
    n_nodes = 20
    pipe_type.parameters["Number_of_Radial_Soil_Nodes"] = n_nodes

    mylist = list(pipe_type.parameters.data.keys())
    sub = 'Radial_Distance_of_Node_'
    actual = len([s for s in mylist if sub.lower() in s.lower()])

    assert actual == n_nodes


def test_cycles_2(pipe_type):
    """changing number of fluid nodes from 10 to 20 should create 20 outputs
    for pipe 2 and 20 outputs for pipe 1"""
    n_nodes = 20
    pipe_type.parameters['Number_of_Fluid_Nodes'] = n_nodes

    outputs = pipe_type.outputs
    mylist = list(outputs.data.keys())
    sub_1 = 'Average_Fluid_Temperature_Pipe_1_'
    sub_2 = 'Average_Fluid_Temperature_Pipe_2_'
    expected_1 = len([s for s in mylist if sub_1.lower() in s.lower()])
    expected_2 = len([s for s in mylist if sub_2.lower() in s.lower()])

    assert n_nodes == expected_1
    assert n_nodes == expected_2


def test_cancel_missing_tag(tank_type):
    from pyTrnsysType import TrnsysModel
    with pytest.raises(NotImplementedError):
        with patch('builtins.input', return_value='N'):
            with open("tests/input_files/Type4a.xml") as xml:
                tank = TrnsysModel.from_xml(xml.read())


def test_out_of_bounds(pipe_type):
    """should trigger ValueError because out of bounds"""
    with pytest.raises(ValueError):
        pipe_type.parameters["Number_of_Radial_Soil_Nodes"] = 21


def test_get_attr(fan_type):
    """Test getter for class TypeVariable"""
    in_air_temp = fan_type.inputs['Inlet_Air_Temperature']
    assert in_air_temp


def test_set_attr(fan_type):
    """Test setter for class TypeVariable"""
    new_value = 12
    attr_name = 'Inlet_Air_Temperature'
    fan_type.inputs[attr_name] = new_value

    Q_ = fan_type.inputs[attr_name]
    assert fan_type.inputs[attr_name] == Q_.__class__(new_value, Q_.units)


def test_set_attr_cycle_parameters(pipe_type):
    """Test setter for class TypeVariable"""
    attr_name = 'Radial_Distance_of_Node_1'
    new_value = 0.05
    pipe_type.parameters[attr_name] = new_value

    Q_ = pipe_type.parameters[attr_name]
    assert pipe_type.parameters[attr_name] == Q_.__class__(new_value, Q_.units)


def test_to_deck(fan_type):
    """test to Input File representation of a TrnsysModel"""
    print(fan_type.to_deck())


def test_set_attr_cycle_question(tank_type):
    attr_name = \
        'Besides_the_top_and_bottom_nodes_how_many_other_nodes_are_there_'
    new_value = 10
    tank_type.outputs[attr_name] = new_value

    Q_ = tank_type.outputs[attr_name]
    assert tank_type.outputs[attr_name] == Q_.__class__(new_value, Q_.units)


def test_set_attr_cycle_question_2(tank_type):
    attr_name = \
        "How_many_temperature_levels_nodes_should_be_used_in_the_tank_"
    new_value = 10
    tank_type.parameters[attr_name] = new_value

    Q_ = tank_type.parameters[attr_name]
    assert tank_type.parameters[attr_name] == Q_.__class__(new_value, Q_.units)


def test_trnsysmodel_repr(tank_type):
    """test the __repr__ for :class:`TrnsysModel`"""
    assert str(tank_type) == 'Type4: Storage Tank; Fixed Inlets, Uniform Losses'


def test_typecycle_repr(tank_type):
    assert repr(tank_type._meta.cycles[0]) == 'output 1 to 13'


def test_collections_repr(tank_type):
    assert repr(tank_type.inputs) == str(tank_type.inputs)
    assert repr(tank_type.outputs) == str(tank_type.outputs)
    assert repr(tank_type.parameters) == str(tank_type.parameters)


def test_TypeVariable_repr(tank_type):
    for _, a in tank_type.inputs.data.items():
        assert repr(a) == 'Hot-side temperature'
        break
    for _, a in tank_type.outputs.data.items():
        assert repr(a) == 'Temperature to heat source'
        break
    for _, a in tank_type.parameters.data.items():
        assert repr(a) == 'Fixed inlet positions'
        break


def test_set_wrong_type(fan_type):
    """try to assign a complexe number should raise a TypeError"""
    with pytest.raises(TypeError):
        fan_type.parameters['Rated_Volumetric_Flow_Rate'] = 2 + 3j


@pytest.mark.parametrize('type_', [int, 'integer', 'real',
                                   pytest.param('complexe',
                                                marks=pytest.mark.xfail(
                                                    raises=NotImplementedError))])
def test_parse_type(type_):
    from pyTrnsysType import parse_type
    parse_type(type_)
