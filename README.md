[![PyPI version fury.io](https://badge.fury.io/py/trnsystor.svg)](https://pypi.python.org/pypi/trnsystor/)
[![codecov](https://codecov.io/gh/samuelduchesne/trnsystor/branch/master/graph/badge.svg?token=kY9pzjlDZJ)](https://codecov.io/gh/samuelduchesne/trnsystor)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/trnsystor.svg)](https://pypi.python.org/pypi/trnsystor/)

# trnsystor

A python scripting language for TRNSYS.

Create .dck files from stratch in an object-oriented python structure. Add components,
specify parameters, connect components together and more throught python code.

## Installation

```python
pip install trnsystor
```

## Usage

Since TRNSYS 18, type proformas can be exported to XML schemas. *trnsystor* builds on this
easy to read data structure to easily create TrnsysModels using the most popular scripting
language in the data science community:
[Python](https://www.economist.com/graphic-detail/2018/07/26/python-is-becoming-the-worlds-most-popular-coding-language).

From the xml file of a type proforma, simply create a TrnsysModel object by invoking the
`from_xml()` constructor:

```python
>>> from trnsystor import TrnsysModel
>>> xml = "tests/input_files/Type951.xml"
>>> pipe1 = TrnsysModel.from_xml(xml)
```

Calling `pipe1` will display its Type number and Name:

```python
>>> pipe1
Type951: Ecoflex 2-Pipe: Buried Piping System
```

Then, `pipe1` can be used to **get** and **set** attributes such as inputs, outputs,
parameters and external files. For example, to set the *Number of Fluid Nodes*, simply set
the new value as you would change a dict value:

```python
>>> pipe1.parameters['Number_of_Fluid_Nodes'] = 50
>>> pipe1.parameters['Number_of_Fluid_Nodes']
NNumber of Fluid Nodes; units=-; value=50
The number of nodes into which each pipe will be divided. Increasing the number of nodes will improve the accuracy but cost simulation run-time.
```

Since the *Number of Fluid Nodes* is a cycle parameter, the number of outputs is modified
dynamically:

calling [pipe1.outputs` should display 116 Outputs.

The new outputs are now accessible and can also be accessed with loops:

```python
>>> for i in range(1,50):
...    print(pipe1.outputs["Average_Fluid_Temperature_Pipe_1_{}".format(i)])
Average Fluid Temperature - Pipe 1-1; units=C; value=0.0 celsius
The average temperature of the fluid in the specified node of the first buried pipe.
... *skipping redundant lines*
Average Fluid Temperature - Pipe 1-49; units=C; value=0.0 celsius
The average temperature of the fluid in the specified node of the first buried pipe.
```

## Connecting outputs with inputs

Connecting model outputs to other model inputs is quite straightforward and uses a simple
mapping technique. For example, to map the first two ouputs of `pipe1`to the first two
inputs of `pipe2`, we create a mapping of the form `mapping = {0:0, 1:1}`. In other words,
this means that the output 0 of pipe1 is connected to the input 1 of pipe2 and the output
1 of pipe1 is connected to the output 1 of pipe2. Keep in mind that since python
traditionally uses 0-based indexing, it has been decided that the same logic in this
package even though TRNSYS uses 1-based indexing. The package will internally assign the
1-based index automatically when saving to file.

For convenience, the mapping can also be done using the output/input names such as
`mapping = {'Outlet_Air_Temperature': 'Inlet_Air_Temperature',
'Outlet_Air_Humidity_Ratio': 'Inlet_Air_Humidity_Ratio'}`:

```python
# First let's create a second pipe, by copying the first one:
pipe2 = pipe1.copy()
# Then, connect pipe1 to pipe2:
pipe1.connect_to(pipe2, mapping={0:0, 1:1})
```

## Equations

In the TRNSYS studio, equations are components holding a list of user-defined expressions.
In trnsystor a similar approach has been taken: the `Equation` class handles the creation
of equations and the [EquationCollection` class handles the block of equations. Here's an
example:

First, create a series of Equation by invoking the [from_expression` constructor. This
allows you to input the equation as a string.

```python
>>> from trnsystor import Equation, EquationCollection
>>> equa1 = Equation.from_expression("TdbAmb = [011,001]")
>>> equa2 = Equation.from_expression("rhAmb = [011,007]")
>>> equa3 = Equation.from_expression("Tsky = [011,004]")
>>> equa4 = Equation.from_expression("vWind = [011,008]")
```

One can create a equation block:

```python
>>> equa_col_1 = EquationCollection([equa1, equa2, equa3, equa4],
                                    name='test')
```

## Changing Initial Input Values

To change the initial value of an input, simply call it by name or with it's zero-based
index and set a new value. This new value will be checked against the bounds set by the
proforma as for a regular input or parameter.

```python
>>> pipe1.parameters['Number_of_Fluid_Nodes'] = 50
>>> pipe_type.initial_input_values["Inlet_Fluid_Temperature_Pipe_1"] = 70
>>> pipe_type.initial_input_values["Inlet_Fluid_Temperature_Pipe_1"].default  # or, pipe_type.initial_input_values[0]
70.0 <Unit('degC')>
```

## Creating a Deck file

A deck file (.dck) is created by instanciating a `Deck` object and calling the instance
method `.save()`. The Deck object contains the Simulation Cards and the different models
(components) for the project. The following code block shows one way of creating a Deck
and saving it to file.

```python
>>> from trnsystor import Deck, ControlCards
>>> 
>>> control_card = ControlCards.debug_template(). # Specifies a predefined set of control cards. See section bellow.
>>> cdeck = Deck(name="mydeck", control_cards=control_card, author="jovyan")
>>> 
>>> list_models = []  # a list of TrnsysModel objects created earlier
>>>  
>>> deck.update_models(list_models)
>>> 
>>> deck.save("my_project.dck")
```

### Simulation Cards

The Simulation Cards is a chuck of code that informs TRNSYS of various simulation controls
such as start time end time and time-step. trnsystor implements many of those *Statements*
with a series of Statement objects.

For instance, to create simulation cards using default values, simply call the `all()`
constructor:

```python
>>> from trnsystor import ControlCards
>>> cc = ControlCards.all()
>>> print(cc)
*** Control Cards
SOLVER 0 1 1          ! Solver statement    Minimum relaxation factor   Maximum relaxation factor
MAP                   ! MAP statement
NOLIST                ! NOLIST statement
NOCHECK 0             ! CHECK Statement
DFQ 1                 ! TRNSYS numerical integration solver method
SIMULATION 0 8760 1   ! Start time  End time    Time step
TOLERANCES 0.01 0.01  ! Integration Convergence
LIMITS 25 10 25       ! Max iterations  Max warnings    Trace limit
EQSOLVER 0            ! EQUATION SOLVER statement
```

### Selecting elements of components

Inputs, Outputs, Parameters, Derivatives, SpecialCards and ExternalFiles can be accessed
via their attribute in any TrnsysModel component. They are accessed via their position as
for in a list. It is also possible to `slice` the collection to retrieved more than one
element. In this case a list is returned:

```python
>>> from trnsystor.trnsysmodel import TrnsysModel
>>> pipe = TrnsysModel.from_xml("tests/input_files/Type951.xml")
>>> pipe.inputs[0:2]  # getting the first 2 inputs
[Inlet Fluid Temperature - Pipe 1; units=C; value=15.0 °C
The temperature of the fluid flowing into the first buried horizontal pipe., Inlet Fluid Flowrate - Pipe 1; units=(kg)/(hr); value=0.0 kg/hr
The flowrate of fluid into the first buried horizontal pipe.]

```

