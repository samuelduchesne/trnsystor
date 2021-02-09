.. _reference:

Reference
=========

Main Classes
------------

.. currentmodule:: pyTrnsysType
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    Constant
    Equation
    ControlCards
    Deck
    TrnsysModel
    Parameter
    Input
    Output

Trnsys Statements
-----------------

.. currentmodule:: pyTrnsysType.statement
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference

    Statement
    Version
    NaNCheck
    OverwriteCheck
    TimeReport
    List
    Simulation
    Tolerances
    Limits
    DFQ
    NoCheck
    NoList
    Map
    EqSolver
    End
    Solver

Helper Classes
--------------

.. currentmodule:: pyTrnsysType
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    MetaData
    Component
    ExternalFile
    TypeVariable
    TypeCycle
    Derivative
    StudioHeader
    LinkStyle
    AnchorPoint

Collections
-----------

.. currentmodule:: pyTrnsysType.collections
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference

    ConstantCollection
    EquationCollection
    ComponentCollection
    ExternalFileCollection
    CycleCollection
    VariableCollection
    InputCollection
    OutputCollection
    ParameterCollection


Utils
-----

.. currentmodule:: pyTrnsysType.utils
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference

    affine_transform
    get_int_from_rgb
    get_rgb_from_int
    DeckFilePrinter
    print_my_latex
    TypeVariableSymbol

