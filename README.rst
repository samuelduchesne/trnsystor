.. image:: https://travis-ci.com/samuelduchesne/pyTrnsysType.svg?branch=develop
    :target: https://travis-ci.com/samuelduchesne/pyTrnsysType

.. image:: https://coveralls.io/repos/github/samuelduchesne/pyTrnsysType/badge.svg?branch=develop
    :target: https://coveralls.io/github/samuelduchesne/pyTrnsysType?branch=develop


pyTrnsysType
============

A python TRNSYS type parser

Installation
------------

.. code-block:: python

    pip install pytrnsystype


Usage
-----

Since TRNSYS 18, type proformas can be exported to XML schemas. *pyTrnsysType* builds on this easy to read data 
structure to easily create TrnsysModel using the most popular scripting language in the data science community: Python_.

From the xml file of a type proforma, simply create a TrnsysModel object by invoking the `from_xml()` constructor. 
Make sure to pass a string to the method by reading the `_io.TextIOWrapper` produced by the `open()` method:

.. code-block:: python

    >>> from pyTrnsysType import TrnsysModel
    >>> with open("tests/input_files/Type951.xml") as xml:
    ...     pipe1 = TrnsysModel.from_xml(xml.read())


Calling `pipe1` will display it's Type number and Name:

.. code-block:: python

    >>> pipe1
    Type951: Ecoflex 2-Pipe: Buried Piping System


Then, `pipe1` can be used to **get** and **set** attributes such as inputs, outputs and parameters.
For example, to set the *Number of Fluid Nodes*, simply set the new value as you would change a dict value:

.. code-block:: python

    >>> from pyTrnsysType import TrnsysModel
    >>> with open("tests/input_files/Type951.xml") as xml:
    ...    pipe1 = TrnsysModel.from_xml(xml.read())
    >>> pipe1.parameters['Number_of_Fluid_Nodes'] = 50
    >>> pipe1.parameters['Number_of_Fluid_Nodes']
    Number of Fluid Nodes; units=-; value=50
    The number of nodes into which each pipe will be divided. Increasing the number of nodes will improve the accuracy but cost simulation run-time.


Since the *Number of Fluid Nodes* is a cycle parameter, the number of outputs is modified dynamically:

calling `pipe1.outputs` should display 116 Outputs.

The new outputs are now accessible and can also be accessed with loops:

.. code-block:: python

    for i in range(1,50):
        print(pipe1.outputs["Average_Fluid_Temperature_Pipe_1_{}".format(i)])


Connecting outputs with inputs
------------------------------

Connecting model outputs to other model inputs is quite straightforward and uses a simple mapping technique. For 
example, to map the first two ouputs of `pipe1` to the first two outputs of `pipe2`, we create a mapping of the form 
`mapping = {0:0, 1:1}`. In other words, this means that the output 0 of pipe1 is connected to the input 1 of pipe2 
and the output 1 of pipe1 is connected to the output 1 of pipe2. Keep in mind that since python traditionally uses  
0-based indexing, it has been decided the same logic in this package even though TRNSYS uses 1-based indexing. The 
package will internally assign the 1-based index.

For convenience, the mapping can also be done using the output/input names such as `mapping = 
{'Outlet_Air_Temperature': 'Inlet_Air_Temperature', 'Outlet_Air_Humidity_Ratio': 'Inlet_Air_Humidity_Ratio'}`:

.. code-block:: python

    # First let's create a second pipe, by copying the first one:
    pipe2 = pipe1.copy()
    # Then, connect pipe1 to pipe2:
    pipe1.connect_to(pipe2, mapping={0:0, 1:1})


Simulation Cards
----------------

The Simulation Cards is a chuck of code that informs TRNSYS of various simulation constrols such as start time end 
time and time-step. pyTrnsysType implements many of those *Statements* with a series of Statement objects.

For instance, to create simulation cards using default values, simply call the `all()` constructor:

.. code-block:: python

    >>> from pyTrnsysType import ControlCards
    >>> cc = ControlCards.all()
    >>> print(cc)
    *** Control Cards
    SOLVER 0 1 1          ! Solver statement	Minimum relaxation factor	Maximum relaxation factor
    MAP                   ! MAP statement
    NOLIST                ! NOLIST statement
    NOCHECK 0             ! CHECK Statement
    DFQ 1                 ! TRNSYS numerical integration solver method
    SIMULATION 0 8760 1   ! Start time	End time	Time step
    TOLERANCES 0.01 0.01  ! Integration	Convergence
    LIMITS 25 10 25       ! Max iterations	Max warnings	Trace limit
    EQSOLVER 0            ! EQUATION SOLVER statement


Equations
---------

In the TRNSYS studio, equations are components holding a list of user-defined expressions. In pyTrnsysType a similar 
approach has been taken: the `Equation` class handles the creation of equations and the `EquationCollection` class 
handles the block of equations. Here's an example:

First, create a series of Equation by invoking the `from_expression` constructor. This allows you two input the 
equation as a string.

.. code-block:: python

    >>> from pyTrnsysType import Equation, EquationCollection
    >>> equa1 = Equation.from_expression("TdbAmb = [011,001]")
    >>> equa2 = Equation.from_expression("rhAmb = [011,007]")
    >>> equa3 = Equation.from_expression("Tsky = [011,004]")
    >>> equa4 = Equation.from_expression("vWind = [011,008]")

One can create

.. code-block:: python

    >>> equa_col_1 = EquationCollection([equa1, equa2, equa3, equa4],
                                        name='test')


.. _Python: https://www.economist.com/graphic-detail/2018/07/26/python-is-becoming-the-worlds-most-popular-coding-language
