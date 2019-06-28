import pytest


@pytest.fixture()
def fan_type():
    """Fixture to create a TrnsysModel from xml"""
    from pyTrnsysType import TrnsysModel
    with open("Tests/input_files/Type146.xml") as xml:
        fan1 = TrnsysModel.from_xml(xml.read())
    yield fan1


def test_get_attr(fan_type):
    """Test getter for class TypeVariable"""
    in_air_temp = fan_type.inputs['Inlet_Air_Temperature']
    assert in_air_temp


def test_set_attr(fan_type):
    """Test setter for class TypeVariable"""
    fan_type.inputs['Inlet_Air_Temperature'] = 12

    Q_ = fan_type.inputs['Inlet_Air_Temperature']
    assert fan_type.inputs['Inlet_Air_Temperature'] == Q_.__class__(12,
                                                                    Q_.units)
