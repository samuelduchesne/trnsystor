import pytest


@pytest.fixture()
def fan_type():
    from pyTrnsysType import TrnsysModel
    with open("Tests/input_files/Type146.xml") as xml:
        fan1 = TrnsysModel.from_xml(xml.read())
    yield fan1

def test_set_attr(fan_type):
    fan_type.parameters.Humidity_Mode = 10