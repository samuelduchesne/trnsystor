"""Test module."""
import os
import sys
from tempfile import NamedTemporaryFile, TemporaryFile

import pytest
from mock import patch
from path import Path
from shapely.geometry import LineString, Point

from trnsystor.component import Component
from trnsystor.trnsysmodel import TrnsysModel


@pytest.fixture(scope="class")
def fan_type():
    """Fixture to create a TrnsysModel from xml."""
    from trnsystor.trnsysmodel import TrnsysModel

    fan1 = TrnsysModel.from_xml(Path("tests/input_files/Type146.xml"))
    yield fan1


@pytest.fixture(scope="class")
def pipe_type():
    """Fixture to create a TrnsysModel from xml. Also tests using a Path."""
    from trnsystor.trnsysmodel import TrnsysModel

    pipe = TrnsysModel.from_xml("tests/input_files/Type951.xml")
    yield pipe


@pytest.fixture(scope="class")
def tank_type():
    from trnsystor.trnsysmodel import TrnsysModel

    with patch("builtins.input", return_value="y"):
        tank = TrnsysModel.from_xml("tests/input_files/Type4a.xml")
        yield tank


@pytest.fixture()
def plotter():
    plot = TrnsysModel.from_xml("tests/input_files/Type65d.xml")
    yield plot


@pytest.fixture(scope="class")
def weather_type():
    from trnsystor.trnsysmodel import TrnsysModel

    with patch("builtins.input", return_value="y"):
        weather = TrnsysModel.from_xml("tests/input_files/Type15-3.xml")
        yield weather


class TestTrnsysModel:
    @patch("builtins.input", return_value="y")
    def test_chiller_type(self, input):
        """Fixture to create a TrnsysModel from xml that contains unknown tags.

        Should prompt user. Passes when input == 'y'
        """
        from trnsystor.trnsysmodel import TrnsysModel

        fan1 = TrnsysModel.from_xml("tests/input_files/Type107-simplified.xml")
        return fan1

    def test_unit_name(self, pipe_type):
        assert pipe_type.unit_name == "Type951"

    def test_cycles(self, pipe_type):
        n_nodes = 20
        pipe_type.parameters["Number_of_Radial_Soil_Nodes"] = n_nodes

        mylist = list(pipe_type.parameters.keys())
        sub = "Radial_Distance_of_Node_"
        actual = len([s for s in mylist if sub.lower() in s.lower()])

        assert pipe_type.parameters["Radial_Distance_of_Node_1"].idx == 27
        assert pipe_type.parameters["Radial_Distance_of_Node_1"].one_based_idx == 28
        assert actual == n_nodes

    def test_cycles_2(self, pipe_type):
        """changing number of fluid nodes from 100 to 20 should create 20 outputs.

        for pipe 2 and 20 outputs for pipe 1
        """
        outputs = pipe_type.outputs
        mylist = list(outputs.keys())
        sub_1 = "Average_Fluid_Temperature_Pipe_1_"
        sub_2 = "Average_Fluid_Temperature_Pipe_2_"
        expected_1 = len([s for s in mylist if sub_1.lower() in s.lower()])
        expected_2 = len([s for s in mylist if sub_2.lower() in s.lower()])

        assert 100 == expected_1
        assert 100 == expected_2

        n_nodes = 20
        pipe_type.parameters["Number_of_Fluid_Nodes"] = n_nodes

        outputs = pipe_type.outputs
        mylist = list(outputs.keys())
        sub_1 = "Average_Fluid_Temperature_Pipe_1_"
        sub_2 = "Average_Fluid_Temperature_Pipe_2_"
        expected_1 = len([s for s in mylist if sub_1.lower() in s.lower()])
        expected_2 = len([s for s in mylist if sub_2.lower() in s.lower()])

        assert n_nodes == expected_1
        assert n_nodes == expected_2

    def test_cycles_issue14(self):
        """https://github.com/samuelduchesne/trnsystor/issues/14."""
        from trnsystor.trnsysmodel import TrnsysModel

        valve = TrnsysModel.from_xml("tests/input_files/Type647.xml")
        assert valve.parameters["Number_of_Outlet_Ports"].value == 2
        assert valve.outputs["Outlet_Flowrate_1"]
        assert valve.outputs["Outlet_Flowrate_2"]
        with pytest.raises(KeyError):
            # Make sure the cyclebase is not returned
            assert valve.outputs["Outlet_Flowrate"]

    def test_cycles_order(self):
        from trnsystor.trnsysmodel import TrnsysModel

        weather_type = TrnsysModel.from_xml("tests/input_files/Type15-3.xml")

        assert weather_type.outputs[24].name == "Beam radiation for surface-1"

        weather_type.parameters["Number_of_surfaces"] = 2

        assert weather_type.outputs[26].name == "Beam radiation for surface-2"

    def test_cancel_missing_tag(self, tank_type):
        from bs4 import BeautifulSoup

        from trnsystor.trnsysmodel import TrnsysModel

        with pytest.raises(NotImplementedError):
            with patch("builtins.input", return_value="N"):
                with open("tests/input_files/Type4a.xml") as xml:
                    soup = BeautifulSoup(xml, "xml")
                    new_tag = soup.new_tag("obscureTag")
                    new_tag.string = "this is a test"
                    soup.find("TrnsysModel").append(new_tag)
                with NamedTemporaryFile("w", delete=False) as tmp:
                    tmp.write(str(soup))
                    tmp.close()
                    TrnsysModel.from_xml(tmp.name)
                    os.unlink(tmp.name)

    def test_out_of_bounds(self, pipe_type):
        """Trigger ValueError because out of bounds."""
        with pytest.raises(ValueError):
            pipe_type.parameters["Number_of_Radial_Soil_Nodes"] = 21

    def test_get_attr(self, fan_type):
        """Test getter for class TypeVariable."""
        in_air_temp = fan_type.inputs["Inlet_Air_Temperature"]
        assert in_air_temp

    def test_set_attr(self, fan_type):
        """Test setter for class TypeVariable."""
        new_value = 12
        attr_name = "Inlet_Air_Temperature"
        fan_type.inputs[attr_name] = new_value

        Q_ = fan_type.inputs[attr_name].value
        assert fan_type.inputs[attr_name].value == Q_.__class__(new_value, Q_.units)

    def test_set_attr_quantity(self, fan_type):
        """Test setter for class TypeVariable with type _Quantity.

        This tests setting a value with different but equivalent units.
        """
        attr_name = "Rated_Volumetric_Flow_Rate"
        new_value = fan_type.parameters[attr_name].value.to("m^3/s") * 10
        fan_type.parameters[attr_name] = new_value

        assert fan_type.parameters[attr_name].value == new_value.to("l/s")

    def test_get_initial_input_values(self, tank_type):
        print(tank_type.initial_input_values)

    def test_set_initial_input_values(self, fan_type):
        new_value = -20
        attr_name = "Inlet_Air_Temperature"
        fan_type.initial_input_values[attr_name] = new_value
        assert fan_type.initial_input_values[attr_name]

    def test_get_attr_derivative(self, tank_type):
        """Test setter for class Derivative."""
        attr_name = "Initial_temperature_of_node_1"
        assert tank_type.derivatives[attr_name].value.m == 50.0

    def test_set_attr_derivative(self, tank_type):
        """Test setter for class Derivative."""
        attr_name = "Initial_temperature_of_node_1"
        tank_type.derivatives[attr_name] = 60
        assert tank_type.derivatives[attr_name].value.m == 60.0

    def test_get_attr_specialCards(self, plotter: TrnsysModel):
        assert plotter.special_cards
        assert plotter.special_cards[0].name == "LABELS"
        print(plotter.special_cards)

    def test_set_attr_cycle_parameters(self, pipe_type):
        """Test setter for class TypeVariable."""
        attr_name = "Radial_Distance_of_Node_1"
        new_value = 0.05
        pipe_type.parameters[attr_name] = new_value

        Q_ = pipe_type.parameters[attr_name].value
        assert pipe_type.parameters[attr_name].value == Q_.__class__(
            new_value, Q_.units
        )

    def test_to_deck(self, fan_type):
        """Test to Input File representation of a TrnsysModel."""
        print(fan_type._to_deck())

    def test_initial_input_values_to_deck(self, fan_type):
        """Test to Input File representation of a TrnsysModel."""
        print(fan_type.initial_input_values._to_deck())

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
        """Test the __repr__ for :class:`TrnsysModel`."""
        assert (
            repr(tank_type)[3:] == "Type4: Storage Tank; Fixed Inlets, Uniform Losses"
        )

    def test_typecycle_repr(self, tank_type):
        """Test the __repr__ for :class:`TypeCycle`."""
        assert repr(tank_type._meta.cycles[0]) == "output 1 to 13"

    def test_collections_repr(self, tank_type):
        assert repr(tank_type.inputs)
        assert repr(tank_type.outputs)
        assert repr(tank_type.parameters)

    def test_TypeVariable_repr(self, tank_type):
        for _, a in tank_type.inputs.items():
            assert float(a) == 45.0
            assert (
                repr(a) == "Hot-side temperature; units=C; value=45.0 °C\nThe"
                " temperature of the fluid flowing into the tank from "
                "the heat source. The inlet location for this hot-side "
                "fluid is one element below the upper auxiliary heating"
                " element."
            )
            break
        for _, a in tank_type.outputs.items():
            assert float(a) == 0.0
            assert (
                repr(a) == "Temperature to heat source; units=C; value=0.0 "
                "°C\nThe temperature of the fluid flowing from the"
                " bottom of the storage tank and returning to the heat "
                "source (the temperature of the bottom node)."
            )
            break
        for _, a in tank_type.parameters.items():
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
        """Try to assign a complex number should raise a TypeError."""
        with pytest.raises(TypeError):
            fan_type.parameters["Rated_Volumetric_Flow_Rate"] = 2 + 3j

    @pytest.mark.parametrize(
        "type_",
        [
            int,
            "integer",
            "real",
            pytest.param(
                "complex", marks=pytest.mark.xfail(raises=NotImplementedError)
            ),
        ],
    )
    def test_parse_type(self, type_):
        from trnsystor.utils import parse_type

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
                "Outlet_Fluid_Temperature_Pipe_1": "Hot_side_temperature",
                "Outlet_Fluid_Flowrate_Pipe_1": "Hot_side_flowrate",
            },
            pytest.param(None, marks=pytest.mark.xfail(raises=NotImplementedError)),
        ],
        ids=["int_mapping", "str_mapping", "automapping"],
    )
    def test_connect_to(self, pipe_type: Component, tank_type: Component, mapping):
        pipe_type.invalidate_connections()
        pipe_type.connect_to(tank_type, mapping=mapping)
        for key, value in mapping.items():
            if pipe_type.outputs[key].is_connected:
                assert pipe_type.outputs[key] == tank_type.inputs[value].predecessor
                assert tank_type.inputs[value] in pipe_type.outputs[key].successors

        # test that connecting to anything else than a TrnsysModel raises a
        # TypeError exception
        with pytest.raises(TypeError):
            pipe_type.connect_to(0)

        # connecting to objects already connected should raise an error
        with pytest.raises(ValueError):
            pipe_type.connect_to(tank_type, mapping=mapping)

    def test_connect_eqcollection_to_type(self, fan_type, tank_type):
        from trnsystor.collections.equation import EquationCollection
        from trnsystor.statement.equation import Equation

        ec = EquationCollection(Equation.from_expression("my=b"))
        ec.set_canvas_position((50, 50))
        ec.connect_to(fan_type, mapping={0: 0}, link_style_kwargs={})

        assert ec.predecessors

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
        from trnsystor.externalfile import ExternalFile

        assert isinstance(weather_type.external_files[0], ExternalFile)
        assert isinstance(
            weather_type.external_files["Which_file_contains_the_Energy_weather_data_"],
            ExternalFile,
        )

    def test_set_external_file(self, weather_type):
        """Test setting a different path for external files."""
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
        from trnsystor.trnsysmodel import TrnsysModel

        dr = TrnsysModel.from_xml("tests/input_files/Type9c.xml")
        assert dr._meta.compileCommand.text == r"df /c"

    def test_set_position(self, fan_type):
        fan_type.set_canvas_position((50, 40))
        assert fan_type.studio.position == Point(50, 40)

    def test_set_link_style_to_itself_error(self, fan_type):
        """Setting a link style on an non-existent connection should raise KeyError."""
        fan_type.invalidate_connections()
        with pytest.raises(KeyError):
            fan_type.set_link_style(fan_type)

    def test_set_link_style_to_itself(self, fan_type):
        fan_type.connect_to(fan_type, mapping={0: 0})
        fan_type.set_link_style(fan_type)

    def test_plot(self, fan_type: TrnsysModel):
        fan_type.plot()

    def test_set_link_style(self, fan_type):
        fan2 = fan_type.copy()
        fan2.set_canvas_position((100, 100))
        fan_type.connect_to(fan2, mapping={0: 0, 1: 1})
        fan_type.set_link_style(fan2, loc=("top-left", "top-right"))
        [print(stl) for stl in fan_type.link_styles]

        with pytest.raises(ValueError):
            # In case None is passed, should raise Value Error
            fan_type.set_link_style(None, loc=("top-left", "top-right"))

    def test_set_link_path(self, fan_type: Component):
        fan2 = fan_type.copy()
        fan_type.set_canvas_position((80, 80))
        fan2.set_canvas_position((10, 10))
        path = LineString([(80, 80), (15, 80), (10, 10)])
        fan_type.connect_to(
            fan2, mapping={0: 0, 1: 1}, link_style_kwargs={"loc": "best", "path": path}
        )

    def test_set_link_style_best(self, fan_type):
        fan2 = fan_type.copy()
        fan2.set_canvas_position((100, 50))
        fan_type.connect_to(fan2, mapping={0: 0, 1: 1})
        fan_type.set_link_style(fan2, loc="best")
        [print(stl) for stl in fan_type.link_styles]

    @pytest.mark.xfail()
    def test_set_anchor_point(self, pipe_type):
        pipe2 = pipe_type.copy()
        pipe_type.connect_to(pipe2, mapping={0: 0})

    def test_affine_transform(self):
        from trnsystor.utils import affine_transform

        geom = Point(10, 10)
        affine_transform(geom, matrix=None)

    def test_get_rgb_int(self):
        from trnsystor.utils import get_rgb_from_int

        assert get_rgb_from_int(9534163) == (211, 122, 145)

    def test_get_int_from_rgb(self):
        from trnsystor.utils import get_int_from_rgb

        assert get_int_from_rgb((211, 122, 145)) == 9534163


class TestStatements:
    def test_statement_class(self):
        from trnsystor.statement.statement import Statement

        statement = Statement()
        assert print(statement) is None

    def test_version_statement(self):
        from trnsystor.statement.version import Version

        ver = Version(v=(17, 3))
        assert ver._to_deck() == "VERSION 17.3"

    def test_simulation_statement(self):
        from trnsystor.statement.simulation import Simulation

        simul = Simulation(0, 8760, 1)
        assert simul._to_deck() == "SIMULATION 0 8760 1"

    def test_tolerances_statement(self):
        from trnsystor.statement.tolerances import Tolerances

        tol = Tolerances(0.001, 0.001)
        assert tol._to_deck() == "TOLERANCES 0.001 0.001"

    def test_limits_statement(self):
        from trnsystor.statement.limites import Limits

        lim = Limits(20, 50)
        assert lim._to_deck() == "LIMITS 20 50 20"

    def test_dfq_statement(self):
        from trnsystor.statement.dfq import DFQ

        dfq_statement = DFQ(3)
        assert dfq_statement._to_deck() == "DFQ 3"

    def test_width_statement(self):
        from trnsystor.statement.width import Width

        width_statement = Width(80)
        assert width_statement._to_deck() == "WIDTH 80"
        with pytest.raises(ValueError):
            Width(1000)

    def test_nocheck_statement(self, fan_type):
        from trnsystor.statement.nocheck import NoCheck

        fan_type.copy()
        fan_type._unit = 1  # we need to force the id to one here
        no_check = NoCheck(inputs=list(fan_type.inputs.values()))
        assert (
            no_check._to_deck() == "NOCHECK 7\n1, 1	1, 2	1, 3	1, " "4	1, " "5	1, 6	1, 7"
        )

        with pytest.raises(ValueError):
            # check exceeding input limits. Multiply list by 10.
            no_check = NoCheck(inputs=list(fan_type.inputs.values()) * 10)

    def test_nolist_statement(self):
        from trnsystor.statement.nolist import NoList

        no_list = NoList(active=True)
        assert no_list._to_deck() == "NOLIST"
        no_list = NoList(active=False)
        assert no_list._to_deck() == ""

    @pytest.mark.parametrize("classmethod", ["all", "debug_template", "basic_template"])
    def test_control_cards(self, classmethod):
        """Call different class methods on ControlCards."""
        from trnsystor.controlcards import ControlCards

        cc = getattr(ControlCards, classmethod)()
        print(cc._to_deck())

    def test_nancheck_statement(self):
        from trnsystor.statement.nancheck import NaNCheck

        nan_check = NaNCheck(n=1)
        assert nan_check._to_deck() == "NAN_CHECK 1"
        nan_check = NaNCheck(n=0)
        assert nan_check._to_deck() == "NAN_CHECK 0"

    def test_overwritecheck_statement(self):
        from trnsystor.statement.overwritecheck import OverwriteCheck

        nan_check = OverwriteCheck(n=1)
        assert nan_check._to_deck() == "OVERWRITE_CHECK 1"
        nan_check = OverwriteCheck(n=0)
        assert nan_check._to_deck() == "OVERWRITE_CHECK 0"

    def test_timereport_statement(self):
        from trnsystor.statement.timereport import TimeReport

        nan_check = TimeReport(n=1)
        assert nan_check._to_deck() == "TIME_REPORT 1"
        nan_check = TimeReport(n=0)
        assert nan_check._to_deck() == "TIME_REPORT 0"


class TestConstantsAndEquations:
    @pytest.fixture()
    def equation(self):
        from trnsystor.statement.equation import Equation

        equa1 = Equation()

        yield equa1

    @pytest.fixture()
    def equation_block(self):
        from trnsystor.collections.equation import EquationCollection
        from trnsystor.statement.equation import Equation

        equa1 = Equation.from_expression("TdbAmb = [011,001]")
        equa2 = Equation.from_expression("rhAmb = [011,007]")
        equa3 = Equation.from_expression("Tsky = [011,004]")
        equa4 = Equation.from_expression("vWind = [011,008]")

        equa_col_1 = EquationCollection([equa1, equa2, equa3, equa4], name="test")
        yield equa_col_1

    @pytest.fixture()
    def constant(self):
        from trnsystor.statement.constant import Constant

        c_1 = Constant()

        assert c_1.constant_number > 1
        yield c_1

    @pytest.fixture()
    def constant_block(self):
        from trnsystor.collections.constant import ConstantCollection
        from trnsystor.statement.constant import Constant

        c_1 = Constant.from_expression("A = 1", doc="A is a constant")
        c_2 = Constant.from_expression("B = 2")
        c_3 = Constant.from_expression("C = A * B + 2")

        c_block = ConstantCollection([c_1, c_2, c_3], name="test constants")

        yield c_block

    def test_unit_number(self, equation_block):
        """Equation block unit numbers are negative."""
        assert equation_block.unit_number < 0

    def test_symbolic_expression(self, tank_type, fan_type):
        from trnsystor.statement.constant import Constant

        name = "var_a"
        exp = "log(a) + (b / 12 - c) * d"
        from trnsystor.statement.equation import Equation

        start = Equation("start", 0)
        cp = Constant("specific_heat", 4.19)
        eq = Equation.from_symbolic_expression(
            name, exp, *(tank_type.outputs[0], start, fan_type.outputs[0], cp)
        )
        print(eq)

    def test_symbolic_expression_2(self, tank_type, fan_type):
        from trnsystor.statement.equation import Equation

        build_loop = "QBuildingLoop"
        cap = "capacity"
        load = "load"

        exp_build_loop = "Lt(l, c)*l + Ge(l, c)*c"
        eq = Equation.from_symbolic_expression(build_loop, exp_build_loop, *(load, cap))
        print(eq)

    def test_malformed_symbolic_expression(self, tank_type, fan_type):
        """Pass only two args while expression asks for 3."""
        name = "var_a"
        exp = "log(a) + b / 12 - c"
        from trnsystor.statement.equation import Equation

        start = Equation("start", 0)
        with pytest.raises(AttributeError):
            Equation.from_symbolic_expression(name, exp, (tank_type.outputs[0], start))

    def test_empty_equationcollection(self):
        from trnsystor.collections.equation import EquationCollection

        eq = EquationCollection()
        assert eq is not None

    def test_equation_collection(self, equation_block):
        from trnsystor.collections.equation import EquationCollection
        from trnsystor.statement.equation import Equation

        equa_col_2 = EquationCollection(
            [equa for equa in equation_block.values()], name="test2"
        )

        assert equation_block.name != equa_col_2.name
        assert equation_block.size == 4
        assert equation_block._to_deck() == equation_block._to_deck()

        # An equal sign needs to be included in an expression
        with pytest.raises(ValueError):
            Equation.from_expression("TdbAmb : [011,001]")

    def test_update_equation_collection(self, equation_block):
        """Test different .update() recipes."""
        from trnsystor.collections.equation import EquationCollection
        from trnsystor.statement.equation import Equation

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
        from trnsystor.collections.equation import EquationCollection
        from trnsystor.statement.equation import Equation

        fan_type._unit = 1
        equa1 = Equation("T_out", fan_type.outputs[0])
        equa_block = EquationCollection([equa1])
        assert str(equa1) == "T_out = [1, 1]"
        assert (
            str(equa_block) == '* EQUATIONS "None"\n\nEQUATIONS '
            "1\nT_out  =  ["
            "1, 1]"
        )

    def test_two_unnamed_equationcollection(self, fan_type):
        """Make sure objects with same name=None can be created."""
        from trnsystor.collections.equation import EquationCollection
        from trnsystor.statement.equation import Equation

        eq1 = Equation("A", fan_type.outputs[0])
        EquationCollection([eq1])
        EquationCollection([eq1])

    def test_constant_collection(self, constant_block):
        from trnsystor.collections.constant import ConstantCollection

        c_block_2 = ConstantCollection(
            [c for c in constant_block.values()], name="test c block"
        )
        assert constant_block.name != c_block_2.name
        assert constant_block.size == 3
        assert str(constant_block)
        assert str(c_block_2)
        print(constant_block)

    def test_update_constant_collection(self, constant_block):
        """Test different .update() recipes."""
        from trnsystor.collections.constant import ConstantCollection
        from trnsystor.statement.constant import Constant

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

    def test_eq_number(self, equation):
        assert equation.eq_number > 1

    def test_eq_idx(self, equation_block):
        for equation in equation_block.values():
            assert equation.idx >= 0

    def test_eq_one_based_idx(self, equation_block):
        for equation in equation_block.values():
            assert equation.one_based_idx >= 1

    def test_eq_unit_number(self, equation_block):
        for equation in equation_block.values():
            assert equation.unit_number < 1

    def test_eq_is_connected(self, equation_block):
        for equation in equation_block.values():
            assert equation.is_connected is False

        # connect and assert again; they should be connected
        equation_block.connect_to(equation_block, mapping={0: 0, 1: 1, 2: 2, 3: 3})
        for i, equation in enumerate(equation_block.values()):
            assert equation.is_connected is True
            assert equation.predecessor == equation_block[i]


class TestDeck:
    @pytest.fixture(scope="class")
    def deck_file(self):
        yield "tests/input_files/test_deck.dck"

    @pytest.fixture(scope="class")
    def pvt_deck(self, deck_file):
        from trnsystor.deck import Deck

        with patch("builtins.input", return_value="y"):
            dck = Deck.read_file(deck_file, proforma_root="tests/input_files")
            yield dck

    @pytest.mark.xfail(raises=ValueError)
    @pytest.fixture(scope="class")
    def irregular_deck(self):
        from trnsystor.deck import Deck

        file = "tests/input_files/Case600h10.dck"
        with patch("builtins.input", return_value="y"):
            dck = Deck.read_file(file, proforma_root="tests/input_files")
            yield dck

    @pytest.fixture(scope="class")
    def G(self, pvt_deck):
        yield pvt_deck.graph

    @pytest.mark.xfail(raises=ValueError)
    def test_irregular_deck(self, irregular_deck):
        assert irregular_deck

    def test_update_with_model(self, weather_type, tank_type, pipe_type):
        from trnsystor.controlcards import ControlCards
        from trnsystor.deck import Deck

        cc = ControlCards.basic_template()
        dck = Deck("test", control_cards=cc)

        # update with single component
        dck.update_models(weather_type)
        assert len(dck.models) == 1

        # update with list of components
        dck.update_models([tank_type, pipe_type])
        assert len(dck.models) == 3

    def test_deck_graph(self, pvt_deck, G):
        import matplotlib.pyplot as plt
        import networkx as nx

        print(len(pvt_deck.models))
        assert not nx.is_empty(G)
        pos = {
            unit: tuple((pos.x, pos.y)) if pos else tuple((50, 50))
            for unit, pos in G.nodes(data="pos")
        }
        nx.draw_networkx(G, pos=pos)
        plt.show()

    @pytest.mark.xfail(
        "pygraphviz" not in sys.modules,
        reason="Skipping this test on Travis CI.",
    )
    def test_deck_graphviz(self, pvt_deck, G):
        import matplotlib.pyplot as plt
        import networkx as nx

        pos = nx.nx_agraph.graphviz_layout(G, "dot")
        nx.draw_networkx(G, pos=pos)
        plt.show()

    def test_cycles(self, G):
        import networkx as nx

        cycles = nx.find_cycle(G)
        print(cycles)

    @pytest.mark.skip("Known fail")
    def test_print(self, deck_file, pvt_deck):
        with open(deck_file, "r") as f:
            pvt_deck_str = f.read().splitlines()
        assert str(pvt_deck).splitlines() == pvt_deck_str

    def test_save(self, pvt_deck):
        pvt_deck.to_file("test.dck", None, "w")


class TestComponent:
    def test_unique_hash(self, fan_type):
        """Copying a component should change its hash."""
        fan_type_2 = fan_type.copy()
        assert hash(fan_type) != hash(fan_type_2)


class TestComponentCollection:
    def test_get_item(self, tank_type, fan_type):
        from trnsystor.collections.components import ComponentCollection

        cc = ComponentCollection([tank_type])
        assert cc.loc[tank_type] == cc.iloc[tank_type.unit_number]
        tank_type._unit = 30
        assert cc.loc[tank_type] == cc.iloc[tank_type.unit_number] == 30
        print(cc.loc.keys())
        print(cc.iloc.keys())
        [print(item) for item in cc]


class TestDeckFormatter:
    @pytest.fixture()
    def deck(self):
        from trnsystor.controlcards import ControlCards
        from trnsystor.deck import Deck

        cc = ControlCards.basic_template()
        yield Deck("Simple Deck", control_cards=cc)

    def test_type951(self, deck):
        from trnsystor.trnsysmodel import TrnsysModel

        model = TrnsysModel.from_xml("tests/input_files/Type951.xml")
        deck.update_models(model)

        with TemporaryFile("w") as deck_file:
            deck.to_file(deck_file, None, "w")

        with open("test_deck.txt", "w") as deck_file:
            deck.to_file(deck_file, None, "w")

        deck.to_file("test_deck.txt")


class TestCommonTypes:
    @pytest.fixture()
    def deck(self, tmp_path):
        from trnsystor.controlcards import ControlCards
        from trnsystor.deck import Deck

        cc = ControlCards.basic_template()
        deck = Deck("Simple Deck", control_cards=cc)
        yield deck

    def test_type951(self, deck, tmp_path):
        from trnsystor.deck import Deck
        from trnsystor.trnsysmodel import TrnsysModel

        d = tmp_path / "sub"
        d.mkdir()
        p = d / "deck_type951.txt"

        model = TrnsysModel.from_xml("tests/input_files/Type951.xml")
        deck.update_models(model)
        deck.to_file(p)
        read_deck = Deck.read_file(p, proforma_root="tests/input_files")
        assert p.read_text() == str(read_deck)


class TestStudioCanvas:
    """TODO: complete tests for Canvas LinkStyles and path positioning."""

    @pytest.mark.skip("known bug when copying type brakes cycles.")
    def test_shortest_path(self, tank_type: TrnsysModel, pipe_type: TrnsysModel):
        pipe_type.set_canvas_position((1, 50))
        tank_type.set_canvas_position((100, 50))
        pipe_type.connect_to(tank_type, mapping={0: 0, 1: 1})

        # create second set of Components
        pipe_type2 = pipe_type.copy()
        tank_type2 = tank_type.copy()
        pipe_type2.set_canvas_position((50, 100))
        tank_type2.set_canvas_position((50, 1))
        pipe_type2.connect_to(tank_type2, mapping={0: 0, 1: 1})

        print(pipe_type2.link_styles)
