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

Since TRNSYS 18, type proformas can exported to XML schemas.
From the xml file representation of a type proforma:

```
from pyTrnsysType import TrnsysModel
with open("Tests/input_files/Type146.xml") as xml:
    fan1 = TrnsysModel.from_xml(xml.read())
```

Get/Set Inputs, Outputs and Parameters and more:

```
print(fan1.parameters.Humidity_Mode)
>>> 
```

Loop trough parameters:

```
for var in fan1.parameters.__dict__.items():
    print(var)
...
>>> ('Humidity_Mode', Humidity Mode)
('Rated_Volumetric_Flow_Rate', Rated Volumetric Flow Rate)
('Rated_Power', Rated Power)
('Motor_Efficiency', Motor Efficiency)
('Motor_Heat_Loss_Fraction', Motor Heat Loss Fraction)
```
