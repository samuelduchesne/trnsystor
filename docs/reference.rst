.. _reference:

Reference
=========

Main Classes
------------

.. currentmodule:: trnsystor
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    statement.Constant
    statement.Equation
    controlcards.ControlCards
    deck.Deck
    TrnsysModel
    typevariable.Parameter
    typevariable.Input
    typevariable.Output
    typevariable.Derivative

Trnsys Statements
-----------------

.. currentmodule:: trnsystor.statement
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

.. currentmodule:: trnsystor
.. autosummary::
    :template: autosummary.rst
    :nosignatures:
    :toctree: reference/

    trnsysmodel.MetaData
    component.Component
    externalfile.ExternalFile
    typevariable.TypeVariable
    typecycle.TypeCycle
    studio.StudioHeader
    linkstyle.LinkStyle
    anchorpoint.AnchorPoint

Collections
-----------

.. currentmodule:: trnsystor.collections
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

.. currentmodule:: trnsystor.utils
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

