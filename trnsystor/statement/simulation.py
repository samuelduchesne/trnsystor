"""Simulation Statement."""

from trnsystor.statement.statement import Statement


class Simulation(Statement):
    """SIMULATION Statement.

    The SIMULATION statement is required for all simulations, and must be
    placed in the TRNSYS input file prior to the first UNIT-TYPE Statement. The
    simulation statement determines the starting and stopping times of the
    simulation as well as the time step to be used.
    """

    def __init__(self, start=0, stop=8760, step=1):
        """Initialize the Simulation Statement.

        Attention:
            With TRNSYS 16 and beyond, the starting time is now specified as the
            time at the beginning of the first time step.

        Args:
            start (int): The hour of the year at which the simulation is to
                begin.
            stop (int): The hour of the year at which the simulation is to end.
            step (float): The time step to be used (hours).
        """
        super().__init__()
        self.start = start
        self.stop = stop
        self.step = step
        self.doc = "Start time\tEnd time\tTime step"

    def _to_deck(self):
        """Return deck representation of self.

        SIMULATION to tf Δt
        """
        return "SIMULATION {} {} {}".format(self.start, self.stop, self.step)
