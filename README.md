[![Build Status](https://travis-ci.com/samuelduchesne/pyTrnsysType.svg?branch=master)](https://travis-ci.com/samuelduchesne/pyTrnsysType)
[![Coverage Status](https://coveralls.io/repos/github/samuelduchesne/pyTrnsysType/badge.svg)](https://coveralls.io/github/samuelduchesne/pyTrnsysType)

pyTrnsysType
============

A python TRNSYS type parser

Installation
------------

```
pip install pytrnsystype
```

Usage
-----

Since TRNSYS 18, type proformas can be exported to XML schemas.
From the xml file representation of a type proforma, simply create a TrnsysModel object:

```python
from pyTrnsysType import TrnsysModel
with open("tests/input_files/Type951.xml") as xml:
    pipe1 = TrnsysModel.from_xml(xml.read())
```

Calling `pipe1` will display it's Type number and Name:

```python
pipe1
Type951: Ecoflex 2-Pipe: Buried Piping System
```

Then, `pipe1` can be used to **get** and **set** attributes such as inputs, outputs and parameters.
For example, to set the *Number of Fluid Nodes*, simply set the new value as you would change a dict value:

```python
pipe1.parameters['Number_of_Fluid_Nodes'] = 50
pipe1.parameters['Number_of_Fluid_Nodes']
<Quantity(50, 'dimensionless')>
```

Since the *Number of Fluid Nodes* is a cycle parameter, the number of outputs is modified dynamically:

calling `pipe1.outputs` should display 116 Outputs.

The new outputs are now accessible and can also be accessed with loops:

```python
for i in range(1,50):
    print(pipe1.outputs["Average_Fluid_Temperature_Pipe_1_{}".format(i)])
```
