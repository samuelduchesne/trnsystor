import tabulate

from .trnsymodel import ParameterCollection, InputCollection


class UnitType(object):
    def __init__(self, n=None, m=None, comment=None):
        """
        Args:
            n (int): the UNIT number of the component. Allowable UNIT numbers
                are integers between 1 and n, where n is set in
                TrnsysConstants.f90 (default = 999).
            m (int): the TYPE number of the component. Allowable TYPE numbers
                are integers between 1 and 999.
            comment (str): Comment is an optional comment. The comment is
                reproduced on the output but is otherwise disregarded. Its
                function is primarily to help the user associate the UNIT and
                TYPE numbers with a particular component in the system.
        """
        self.Comment = comment
        self.n = n
        self.m = m

    def __repr__(self):
        """Overload __repr__() and str() to implement self.to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        return "UNIT {n} TYPE {m} {Comment}\n".format(n=self.n, m=self.m,
                                                      Comment=self.Comment)


class Parameters(object):
    def __init__(self, param_colection, n=None):
        """
        Args:
            param_colection (ParameterCollection): tuple of parameters
            n (int, optional): the number of PARAMETERS to follow on the next
                line(s). Typically this is the number of parameters required by
                the component, but may be less if more than one PARAMETERS
                statement is used for a given component.
        """
        self.v = param_colection
        if not n:
            self.n = self.v.size
        else:
            self.n = n

    def __repr__(self):
        """Overload __repr__() and str() to implement self.to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        head = "PARAMETERS {}\n".format(self.n)
        # loop through parameters and print the (value, name) tuples.
        v_ = ((self.v[param].m, "! {}".format(self.v.data[param].name)) for
              param in self.v)
        params_str = tabulate.tabulate(v_, tablefmt='plain', numalign="left")
        return head + params_str + "\n"


class Inputs(object):
    def __init__(self, input_collection, n=None):
        """

        Args:
            input_collection (InputCollection):
            n:
        """
        self.inputs = input_collection
        if not n:
            self.n = input_collection.size
        else:
            self.n = n

    def __repr__(self):
        """Overload __repr__() and str() to implement self.to_deck()"""
        return self.to_deck()

    def to_deck(self):
        """Returns the string representation for the Input File (.dck)"""
        head = "INPUTS {}\n".format(self.n)
        inputs_str = ""
        return str(head) + str(inputs_str)


class Derivatives:
    pass


class Trace:
    pass


class Format:
    pass
