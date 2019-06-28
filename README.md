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

```
from pyTrnsysType import TrnsysModel
with open("Tests/input_files/Type146.xml") as xml:
    fan1 = TrnsysModel.from_xml(xml.read())
```

Then, `fan1` can be used to get and set attributes such as inputs, outputs and parameters.
Get/Set Inputs, Outputs and Parameters and more:

```
print(fan1.parameters['Humidity_Mode'])
2 dimensionless
>>> 
```

Loop trough parameters:

```
>>> for var in fan1.parameters.__dict__.items():
...     print(var)
...
('data', {'Humidity_Mode': 2 dimensionless, 'Rated_Volumetric_Flow_Rate': 300.0 liter / second, 
'Rated_Power': 2684.0 kilojoule / hour, 'Motor_Efficiency': 0.9 dimensionless, 
'Motor_Heat_Loss_Fraction': 0.0 dimensionless})
>>>
```
