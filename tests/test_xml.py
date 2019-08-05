import os
from tempfile import NamedTemporaryFile

import pytest
from mock import patch
from path import Path
from shapely.geometry import Point, LineString


@pytest.fixture(scope="class")
def fan_type():
    """Fixture to create a TrnsysModel from xml"""
    from pyTrnsysType.trnsymodel import TrnsysModel

    fan1 = TrnsysModel.from_xml(Path("tests/input_files/Type146.xml"))
    yield fan1


@pytest.fixture(scope="class")
def pipe_type():
    """Fixture to create a TrnsysModel from xml. Also tests using a Path"""
    from pyTrnsysType.trnsymodel import TrnsysModel

    pipe = TrnsysModel.from_xml("tests/input_files/Type951.xml")
    yield pipe


@pytest.fixture(scope="class")
def tank_type():
    from pyTrnsysType.trnsymodel import TrnsysModel

    with patch("builtins.input", return_value="y"):
        tank = TrnsysModel.from_xml("tests/input_files/Type4a.xml")
        yield tank


@pytest.fixture(scope="class")
def weather_type():
    from pyTrnsysType.trnsymodel import TrnsysModel

    with patch("builtins.input", return_value="y"):
        weather = TrnsysModel.from_xml("tests/input_files/Type15-3.xml")
        yield weather


class TestTrnsysModel:
    @patch("builtins.input", return_value="y")
    def test_chiller_type(self, input):
        """Fixture to create a TrnsysModel from xml from an xml that contains
        unknown tags. Should primpt user. Passes when input == 'y'"""
        from pyTrnsysType.trnsymodel import TrnsysModel

        fan1 = TrnsysModel.from_xml("tests/input_files/Type107-simplified.xml")
        return fan1

    def test_unit_name(self, pipe_type):
        assert pipe_type.unit_name == "Type951"

    def test_cycles(self, pipe_type):
        n_nodes = 20
        pipe_type.parameters["Number_of_Radial_Soil_Nodes"] = n_nodes

        mylist = list(pipe_type.parameters.data.keys())
        sub = "Radial_Distance_of_Node_"
        actual = len([s for s in mylist if sub.lower() in s.lower()])

        assert actual == n_nodes

    def test_cycles_2(self, pipe_type):
        """changing number of fluid nodes from 10 to 20 should create 20 outputs
        for pipe 2 and 20 outputs for pipe 1"""
        n_nodes = 20
        pipe_type.parameters["Number_of_Fluid_Nodes"] = n_nodes

        outputs = pipe_type.outputs
        mylist = list(outputs.data.keys())
        sub_1 = "Average_Fluid_Temperature_Pipe_1_"
        sub_2 = "Average_Fluid_Temperature_Pipe_2_"
        expected_1 = len([s for s in mylist if sub_1.lower() in s.lower()])
        expected_2 = len([s for s in mylist if sub_2.lower() in s.lower()])

        assert n_nodes == expected_1
        assert n_nodes == expected_2

    def test_cycles_issue14(self):
        from pyTrnsysType.trnsymodel import TrnsysModel

        valve = TrnsysModel.from_xml("tests/input_files/Type647.xml")
        assert valve.parameters["Number_of_Outlet_Ports"].value == 2
        assert valve.outputs["Outlet_Flowrate_1"]
        assert valve.outputs["Outlet_Flowrate_2"]
        with pytest.raises(KeyError):
            # Make sure the cyclebase is not returned
            assert valve.outputs["Outlet_Flowrate"]

    def test_cancel_missing_tag(self, tank_type):
        from pyTrnsysType.trnsymodel import TrnsysModel
        from bs4 import BeautifulSoup

        with pytest.raises(NotImplementedError):
            with patch("builtins.input", return_value="N"):
                with open("tests/input_files/Type4a.xml") as xml:
                    soup = BeautifulSoup(xml, "xml")
                    new_tag = soup.new_tag("obscureTag")
                    new_tag.string = "this is a test"
                    soup.find("TrnsysModel").append(new_tag)
                with NamedTemporaryFile("w") as tmp:
                    tmp.write(str(soup))
                    tank = TrnsysModel.from_xml(tmp.name)

    def test_out_of_bounds(self, pipe_type):
        """should trigger ValueError because out of bounds"""
        with pytest.raises(ValueError):
            pipe_type.parameters["Number_of_Radial_Soil_Nodes"] = 21

    def test_get_attr(self, fan_type):
        """Test getter for class TypeVariable"""
        in_air_temp = fan_type.inputs["Inlet_Air_Temperature"]
        assert in_air_temp

    def test_set_attr(self, fan_type):
        """Test setter for class TypeVariable"""
        new_value = 12
        attr_name = "Inlet_Air_Temperature"
        fan_type.inputs[attr_name] = new_value

        Q_ = fan_type.inputs[attr_name].value
        assert fan_type.inputs[attr_name].value == Q_.__class__(new_value, Q_.units)

    def test_set_attr_quantity(self, fan_type):
        """Test setter for class TypeVariable with type _Quantity. This tests
        setting a value with different but equivalent units"""
        attr_name = "Rated_Volumetric_Flow_Rate"
        new_value = fan_type.parameters[attr_name].value.to("m^3/s") * 10
        fan_type.parameters[attr_name] = new_value

        assert fan_type.parameters[attr_name].value == new_value

    def test_get_attr_derivative(self, tank_type):
        """Test setter for class Derivative"""
        attr_name = "Initial_temperature_of_node_1"
        assert tank_type.derivatives[attr_name].value.m == 50.0

    def test_set_attr_derivative(self, tank_type):
        """Test setter for class Derivative"""
        attr_name = "Initial_temperature_of_node_1"
        tank_type.derivatives[attr_name] = 60
        assert tank_type.derivatives[attr_name].value.m == 60.0

    def test_set_attr_cycle_parameters(self, pipe_type):
        """Test setter for class TypeVariable"""
        attr_name = "Radial_Distance_of_Node_1"
        new_value = 0.05
        pipe_type.parameters[attr_name] = new_value

        Q_ = pipe_type.parameters[attr_name].value
        assert pipe_type.parameters[attr_name].value == Q_.__class__(
            new_value, Q_.units
        )

    def test_to_deck(self, fan_type):
        """test to Input File representation of a TrnsysModel"""
        print(fan_type._to_deck())

    def test_set_attr_cycle_question(self, tank_type):
        attr_name = "Besides_the_top_and_bottom_nodes_how_many_other_nodes_are_there_"
        new_value = 10
        tank_type.outputs[attr_name] = new_value

        Q_ = tank_type.outputs[attr_name].value
        assert tank_type.outputs[attr_name].value == Q_.__class__(new_value, Q_.units)

    def test_set_attr_cycle_question_2(self, tank_type):
        attr_name = "How_many_temperature_levels_nodes_should_be_used_in_the_tank_"
        new_value = 10
        tank_type.parameters[attr_name] = new_value

        Q_ = tank_type.parameters[attr_name].value
        assert tank_type.parameters[attr_name].value == Q_.__class__(
            new_value, Q_.units
        )

    def test_trnsysmodel_repr(self, tank_type):
        """test the __repr__ for :class:`TrnsysModel`"""
        assert str(tank_type) == "Type4: Storage Tank; Fixed Inlets, Uniform Losses"

    def test_typecycle_repr(self, tank_type):
        assert repr(tank_type._meta.cycles[0]) == "output 1 to 13"

    def test_collections_repr(self, tank_type):
        assert repr(tank_type.inputs) == str(tank_type.inputs)
        assert repr(tank_type.outputs) == str(tank_type.outputs)
        assert repr(tank_type.parameters) == str(tank_type.parameters)

    def test_TypeVariable_repr(self, tank_type):
        for _, a in tank_type.inputs.data.items():
            assert float(a) == 45.0
            assert (
                repr(a) == "Hot-side temperature; units=C; value=45.0 celsius\nThe"
                " temperature of the fluid flowing into the tank from "
                "the heat source. The inlet location for this hot-side "
                "fluid is one element below the upper auxiliary heating"
                " element."
            )
            break
        for _, a in tank_type.outputs.data.items():
            assert float(a) == 0.0
            assert (
                repr(a) == "Temperature to heat source; units=C; value=0.0 "
                "celsius\nThe temperature of the fluid flowing from the"
                " bottom of the storage tank and returning to the heat "
                "source (the temperature of the bottom node)."
            )
            break
        for _, a in tank_type.parameters.data.items():
            assert int(a) == 1
            assert (
                repr(a) == "Fixed inlet positions; units=-; value=1\nThe auxiliary"
                " storage tank may operate in one of three modes in "
                "determining the inlet positions of the flow streams. "
                "Mode 1 indicates that the heat source flow enters the "
                "tank in the node located just below the top auxiliary "
                "heating element. The cold source flow enters at the "
                "bottom of the tank. Do not change this parameter."
            )
            break

    def test_set_wrong_type(self, fan_type):
        """try to assign a complexe number should raise a TypeError"""
        with pytest.raises(TypeError):
            fan_type.parameters["Rated_Volumetric_Flow_Rate"] = 2 + 3j

    @pytest.mark.parametrize(
        "type_",
        [
            int,
            "integer",
            "real",
            pytest.param(
                "complexe", marks=pytest.mark.xfail(raises=NotImplementedError)
            ),
        ],
    )
    def test_parse_type(self, type_):
        from pyTrnsysType.utils import parse_type

        parse_type(type_)

    def test_int_indexing(self, fan_type):
        print(fan_type.inputs[0])

    def test_copy_trnsys_model(self, fan_type):
        fan_1 = fan_type
        fan_2 = fan_type.copy()

        # check if sub-objects are copies as well.
        fan_1.parameters[0] = 1

        assert id(fan_1) != id(fan_2)
        assert fan_1.parameters[0].value.m != fan_2.parameters[0].value.m

    @pytest.mark.parametrize(
        "mapping",
        [
            {0: 0, 1: 1},
            {
                "Outlet_Air_Temperature": "Inlet_Air_Temperature",
                "Outlet_Air_Humidity_Ratio": "Inlet_Air_Humidity_Ratio",
            },
            pytest.param(None, marks=pytest.mark.xfail(raises=NotImplementedError)),
        ],
        ids=["int_mapping", "str_mapping", "automapping"],
    )
    def test_connect_to(self, fan_type, mapping):
        fan_type.invalidate_connections()
        fan_2 = fan_type.copy()
        fan_type.connect_to(fan_2, mapping=mapping)
        for key, value in mapping.items():
            if fan_type.outputs[key].is_connected:
                assert fan_type.outputs[key].connected_to == fan_2.inputs[value]

        # test that connecting to anything else than a TrnsysModel raises a
        # TypeError exception
        with pytest.raises(TypeError):
            fan_type.connect_to(0)

        # connecting to objects already connected should raise an error
        with pytest.raises(ValueError):
            fan_type.connect_to(fan_2, mapping=mapping)

    def test_connect_eqcollection_to_type(self, fan_type, tank_type):
        from pyTrnsysType import Equation, EquationCollection

        ec = EquationCollection(Equation.from_expression("my=b"))
        ec.set_canvas_position((500, 500))
        ec.connect_to(fan_type, mapping={0: 0}, link_style={})

        print(fan_type._to_deck())

    def test_to_deck_with_connected(self, fan_type):
        fan_2 = fan_type.copy()
        fan_type.connect_to(fan_2, mapping={0: 0, 1: 1})

        print(fan_2._to_deck())

    def test_magic_type_variables(self, fan_type):
        for input in fan_type.inputs.values():
            assert input * 2 == float(input) * 2
            assert input + 2 == float(input) + 2
            assert input - 2 == float(input) - 2

    def test_external_file(self, weather_type):
        print(weather_type._to_deck())

    def test_get_external_file(self, weather_type):
        from pyTrnsysType.trnsymodel import ExternalFile

        assert isinstance(weather_type.external_files[0], ExternalFile)
        assert isinstance(
            weather_type.external_files["Which_file_contains_the_Energy_weather_data_"],
            ExternalFile,
        )

    def test_set_external_file(self, weather_type):
        """Test setting a different path for external files"""
        from path import Path

        # test set Path behavior
        weather_type.external_files[0] = Path.getcwd()
        assert weather_type.external_files[0].value == Path.getcwd()

        # test set str behavior
        weather_type.external_files[0] = str(Path.getcwd())
        assert weather_type.external_files[0].value == Path.getcwd()

        # test unsupported type set
        with pytest.raises(TypeError):
            weather_type.external_files[0] = 1

    def test_datareader(self):
        from pyTrnsysType.trnsymodel import TrnsysModel

        dr = TrnsysModel.from_xml("tests/input_files/Type9c.xml")
        assert dr._meta.compileCommand.text == r"df /c"

    def test_set_position(self, fan_type):
        fan_type.set_canvas_position((500, 400))
        assert fan_type.studio.position == Point(500, 400)

    def test_set_link_style_to_itself(self, fan_type):
        with pytest.raises(NotImplementedError):
            fan_type.set_link_style(fan_type)

    def test_set_link_style(self, fan_type):
        fan2 = fan_type.copy()
        fan2.set_canvas_position((100, 100))
        fan_type.set_link_style(fan2, loc=("top-left", "top-right"))
        [print(stl) for stl in fan_type.studio.link_styles.values()]

        with pytest.raises(ValueError):
            # In case None is passed, should raise Value Error
            fan_type.set_link_style(None, loc=("top-left", "top-right"))

    def test_set_link_path(self, fan_type):
        fan2 = fan_type.copy()
        fan_type.set_canvas_position((200, 200))
        fan2.set_canvas_position((100, 100))
        path = LineString([(200, 200), (150, 150), (100, 100)])
        fan_type.set_link_style(fan2, loc="best", path=path)

    def test_set_link_style_best(self, fan_type):
        fan2 = fan_type.copy()
        fan2.set_canvas_position((100, 50))
        fan_type.set_link_style(fan2, loc="best")
        [print(stl) for stl in fan_type.studio.link_styles.values()]

    @pytest.mark.xfail()
    def test_set_anchor_point(self, pipe_type):
        pipe2 = pipe_type.copy()
        pipe_type.connect_to(pipe2, mapping={0: 0})

    def test_affine_transform(self):
        from pyTrnsysType.utils import affine_transform

        geom = Point(10, 10)
        affine_transform(geom, matrix=None)

    def test_get_rgb_int(self):
        from pyTrnsysType.utils import get_rgb_from_int

        assert get_rgb_from_int(9534163) == (211, 122, 145)

    def test_get_int_from_rgb(self):
        from pyTrnsysType.utils import get_int_from_rgb

        assert get_int_from_rgb((211, 122, 145)) == 9534163


class TestStatements:
    def test_statement_class(self):
        from pyTrnsysType.statements import Statement

        statement = Statement()
        assert print(statement) == None

    def test_version_statement(self):
        from pyTrnsysType.statements import Version

        ver = Version(v=(17, 3))
        assert ver._to_deck() == "VERSION 17.3"

    def test_simulation_statement(self):
        from pyTrnsysType.statements import Simulation

        simul = Simulation(0, 8760, 1)
        assert simul._to_deck() == "SIMULATION 0 8760 1"

    def test_tolerances_statement(self):
        from pyTrnsysType.statements import Tolerances

        tol = Tolerances(0.001, 0.001)
        assert tol._to_deck() == "TOLERANCES 0.001 0.001"

    def test_limits_statement(self):
        from pyTrnsysType.statements import Limits

        lim = Limits(20, 50)
        assert lim._to_deck() == "LIMITS 20 50 20"

    def test_dfq_statement(self):
        from pyTrnsysType.statements import DFQ

        dfq_statement = DFQ(3)
        assert dfq_statement._to_deck() == "DFQ 3"

    def test_width_statement(self):
        from pyTrnsysType.statements import Width

        width_statement = Width(80)
        assert width_statement._to_deck() == "WIDTH 80"
        with pytest.raises(ValueError):
            wrong_statement = Width(1000)

    def test_nocheck_statement(self, fan_type):
        from pyTrnsysType.statements import NoCheck

        fan_type.copy()
        fan_type._unit = 1  # we need to force the id to one here
        no_check = NoCheck(inputs=list(fan_type.inputs.values()))
        assert no_check._to_deck() == "NOCHECK 7\n1, 1	1, 2	1, 3	1, " "4	1, 5	1, 6	1, 7"

        with pytest.raises(ValueError):
            # check exceeding input limits. Multiply list by 10.
            no_check = NoCheck(inputs=list(fan_type.inputs.values()) * 10)

    def test_nolist_statement(self):
        from pyTrnsysType.statements import NoList

        no_list = NoList(active=True)
        assert no_list._to_deck() == "NOLIST"
        no_list = NoList(active=False)
        assert no_list._to_deck() == ""

    @pytest.mark.parametrize("classmethod", ["all", "debug_template", "basic_template"])
    def test_control_cards(self, classmethod):
        """Call different class methods on ControlCards"""
        from pyTrnsysType.input_file import ControlCards

        cc = getattr(ControlCards, classmethod)()
        print(cc._to_deck())

    def test_nancheck_statement(self):
        from pyTrnsysType.statements import NaNCheck

        nan_check = NaNCheck(n=1)
        assert nan_check._to_deck() == "NAN_CHECK 1"
        nan_check = NaNCheck(n=0)
        assert nan_check._to_deck() == "NAN_CHECK 0"

    def test_overwritecheck_statement(self):
        from pyTrnsysType.statements import OverwriteCheck

        nan_check = OverwriteCheck(n=1)
        assert nan_check._to_deck() == "OVERWRITE_CHECK 1"
        nan_check = OverwriteCheck(n=0)
        assert nan_check._to_deck() == "OVERWRITE_CHECK 0"

    def test_timereport_statement(self):
        from pyTrnsysType.statements import TimeReport

        nan_check = TimeReport(n=1)
        assert nan_check._to_deck() == "TIME_REPORT 1"
        nan_check = TimeReport(n=0)
        assert nan_check._to_deck() == "TIME_REPORT 0"


class TestConstantsAndEquations:
    @pytest.fixture()
    def equation(self):
        from pyTrnsysType.input_file import Equation

        equa1 = Equation()

        assert equa1.eq_number > 1
        yield equa1

    @pytest.fixture()
    def equation_block(self):
        from pyTrnsysType.input_file import Equation, EquationCollection

        equa1 = Equation.from_expression("TdbAmb = [011,001]")
        equa2 = Equation.from_expression("rhAmb = [011,007]")
        equa3 = Equation.from_expression("Tsky = [011,004]")
        equa4 = Equation.from_expression("vWind = [011,008]")

        equa_col_1 = EquationCollection([equa1, equa2, equa3, equa4], name="test")
        yield equa_col_1

    @pytest.fixture()
    def constant(self):
        from pyTrnsysType.input_file import Constant

        c_1 = Constant()

        assert c_1.constant_number > 1
        yield c_1

    @pytest.fixture()
    def constant_block(self):
        from pyTrnsysType.input_file import Constant, ConstantCollection

        c_1 = Constant.from_expression("A = 1", doc="A is a constant")
        c_2 = Constant.from_expression("B = 2")
        c_3 = Constant.from_expression("C = A * B + 2")

        c_block = ConstantCollection([c_1, c_2, c_3], name="test constants")

        yield c_block

    def test_unit_number(self, equation_block):
        assert equation_block.unit_number > 0

    def test_symbolic_expression(self, tank_type, fan_type):
        from pyTrnsysType import Constant

        name = "var_a"
        exp = "log(a) + (b / 12 - c) * d"
        from pyTrnsysType.input_file import Equation

        start = Equation("start", 0)
        cp = Constant("specific_heat", 4.19)
        eq = Equation.from_symbolic_expression(
            name, exp, *(tank_type.outputs[0], start, fan_type.outputs[0], cp)
        )
        print(eq)

    def test_malformed_symbolic_expression(self, tank_type, fan_type):
        """passed only two args while expression asks for 3"""
        from pyTrnsysType import Constant

        name = "var_a"
        exp = "log(a) + b / 12 - c"
        c_ = Constant.from_expression("start=0")
        from pyTrnsysType.input_file import Equation

        start = Equation("start", 0)
        with pytest.raises(AttributeError):
            Equation.from_symbolic_expression(name, exp, (tank_type.outputs[0], start))

    def test_empty_equationcollection(self):
        from pyTrnsysType.input_file import EquationCollection

        eq = EquationCollection()

    def test_equation_collection(self, equation_block):
        from pyTrnsysType.input_file import Equation, EquationCollection

        equa_col_2 = EquationCollection(
            [equa for equa in equation_block.values()], name="test"
        )

        assert equation_block.name != equa_col_2.name
        assert equation_block.size == 4
        assert equation_block._to_deck() == equation_block._to_deck()

        # An equal sign needs to be included in an expression
        with pytest.raises(ValueError):
            equa1 = Equation.from_expression("TdbAmb : [011,001]")

    def test_update_equation_collection(self, equation_block):
        """test different .update() recipes"""
        from pyTrnsysType.input_file import Equation, EquationCollection

        list_equations = [equa for equa in equation_block.values()]

        ec = EquationCollection(name="my equation block")

        # from a list
        ec.update(list_equations)
        assert len(ec) == 4

        # from a dict
        ec.update({eq.name: eq for eq in list_equations})
        assert len(ec) == 4

        # from a single Equation
        eq_x = Equation.from_expression("A=2")
        ec.update(eq_x)
        assert len(ec) == 5

        # raises error if dict value is other than :class:`Equation`
        with pytest.raises(TypeError):
            ec.update({"test": float})

        # update with more than one dicts.
        ec.update(list_equations, F=list_equations)

    def test_equation_with_typevariable(self, fan_type):
        from pyTrnsysType.input_file import Equation, EquationCollection

        fan_type._unit = 1
        equa1 = Equation("T_out", fan_type.outputs[0])
        equa_block = EquationCollection([equa1])
        assert str(equa1) == "T_out = [1, 1]"
        assert (
            str(equa_block) == '* EQUATIONS "None"\n\nEQUATIONS ' "1\nT_out  =  [1, 1]"
        )

    def test_two_unnamed_equationcollection(self, fan_type):
        """make sure objects with same name=None can be created"""
        from pyTrnsysType.input_file import Equation, EquationCollection

        eq1 = Equation("A", fan_type.outputs[0])
        EquationCollection([eq1])
        EquationCollection([eq1])

    def test_constant_collection(self, constant_block):
        from pyTrnsysType.input_file import ConstantCollection

        c_block_2 = ConstantCollection(
            [c for c in constant_block.values()], name="test c block"
        )
        assert constant_block.name != c_block_2.name
        assert constant_block.size == 3
        assert str(constant_block)
        assert str(c_block_2)
        print(constant_block)

    def test_update_constant_collection(self, constant_block):
        """test different .update() recipes"""
        from pyTrnsysType.input_file import Constant, ConstantCollection

        list_constants = [cts for cts in constant_block.values()]

        cc = ConstantCollection(name="my constant block")

        # from a list
        cc.update(list_constants)
        assert len(cc) == 3

        # from a dict
        cc.update({cts.name: cts for cts in list_constants})
        assert len(cc) == 3

        # from a single Equation
        cts_x = Constant.from_expression("D=2")
        cc.update(cts_x)
        assert len(cc) == 4

        # raises error if dict value is other than :class:`Equation`
        with pytest.raises(TypeError):
            cc.update({"test": float})

        # update with more than one dicts.
        cc.update(list_constants, F=list_constants)


class TestDeck:
    @pytest.fixture(scope="class")
    def pvt_deck(self):
        from pyTrnsysType import Deck

        file = "tests/input_files/test_deck.dck"
        with patch("builtins.input", return_value="y"):
            dck = Deck.from_file(file, proforma_root="tests/input_files")
            yield dck

    @pytest.fixture(scope="class")
    def G(self, pvt_deck):
        yield pvt_deck.graph

    def test_update_with_model(self, weather_type, tank_type, pipe_type):
        from pyTrnsysType import Deck, ControlCards

        cc = ControlCards.basic_template()
        dck = Deck("test", cc)

        # update with single component
        dck.update_with_model(weather_type)
        assert len(dck.models) == 1

        # update with list of components
        dck.update_with_model([tank_type, pipe_type])
        assert len(dck.models) == 3

    def test_deck_graph(self, pvt_deck, G):
        import networkx as nx
        import matplotlib.pyplot as plt

        print(len(pvt_deck.models))
        assert not nx.is_empty(G)
        pos = {
            unit: tuple((pos.x, pos.y)) if pos else tuple((50, 50))
            for unit, pos in G.nodes(data="pos")
        }
        nx.draw_networkx(G, pos=pos)
        plt.show()

    @pytest.mark.xfail(
        "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true",
        reason="Skipping this test on Travis CI.",
    )
    def test_deck_graphviz(self, pvt_deck, G):
        import networkx as nx
        import matplotlib.pyplot as plt

        pos = nx.nx_agraph.graphviz_layout(G, "dot")
        nx.draw_networkx(G, pos=pos)
        plt.show()

    def test_cycles(self, G):
        import networkx as nx

        cycles = nx.find_cycle(G)
        print(cycles)

    def test_print(self, pvt_deck):
        print(self, pvt_deck)

    def test_save(self, pvt_deck):
        pvt_deck.save("test.dck")


class TestComponent:
    def test_unique_hash(self, fan_type):
        """copying a component should change its hash"""
        fan_type_2 = fan_type.copy()
        assert hash(fan_type) != hash(fan_type_2)


class TestComponentCollection:
    def test_get_item(self, tank_type, fan_type):
        from pyTrnsysType.trnsymodel import ComponentCollection

        cc = ComponentCollection([tank_type])
        assert cc.loc[tank_type] == cc.iloc[tank_type.unit_number]
        tank_type._unit = 30
        assert cc.loc[tank_type] == cc.iloc[tank_type.unit_number] == 30
        print(cc.loc.keys())
        print(cc.iloc.keys())
        [print(item) for item in cc]
