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

### Connecting outputs with inputs

Connecting model outputs to other model inputs is quite straightforward and uses a simple mapping technique. For 
example, to map the first two ouputs of `pipe1` to the first two outputs of `pipe2`, we create a mapping of the form 
`mapping = {0:0, 1:1}`. In other words, this means that the output 0 of pipe1 is connected to the input 1 of pipe2 
and the output 1 of pipe1 is connected to the output 1 of pipe2. Keep in mind that since python traditionally uses  
0-based indexing, it has been decided the same logic in this package even though TRNSYS uses 1-based indexing. The 
package will internally assign the 1-based index.

For convenience, the mapping can also be done using the output/input names such as `mapping = 
{'Outlet_Air_Temperature': 'Inlet_Air_Temperature', 'Outlet_Air_Humidity_Ratio': 'Inlet_Air_Humidity_Ratio'}`:

```python
# First let's create a second pipe, by copying the first one:
pipe2 = pipe1.copy()
# Then, connect pipe1 to pipe2:
pipe1.connect_to(pipe2, mapping={0:0, 1:1})
```
