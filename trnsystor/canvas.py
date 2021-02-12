"""StudioCanvas module."""
import networkx as nx
from shapely.geometry import LineString, box


class StudioCanvas:
    """StudioCanvas class.

    Handles geometric positioning of Components on a grid.
    """

    def __init__(self, width=2000, height=1000):
        """Initialize object.

        Args:
            width (int): The width of the grid in points.
            height (int): The height of the grid in points.
        """
        self.width = width
        self.height = height

        self._grid_valid = True
        self._grid = None

    @property
    def bbox(self):
        """Return a bounding box rectangle for the canvas."""
        return box(0, 0, self.width, self.height)

    @property
    def grid_is_valid(self):
        """Return True if grid is valid."""
        if self._grid_valid:
            return True
        else:
            return False

    @property
    def grid(self):
        """Return the two-dimensional grid graph of the studio canvas."""
        if self.grid_is_valid and self._grid is not None:
            return self._grid
        else:
            self._grid = nx.grid_2d_graph(self.width, self.height)
            return self._grid

    def invalidate_grid(self):
        """Invalidate grid."""
        self._grid_valid = False

    def resize_canvas(self, width, height):
        """Change the canvas size.

        TODO: Handle grid when canvas size is changed (e.g used paths)

        Args:
            width (int): new width.
            height (int): new height.
        """
        self.width = width
        self.height = height
        self.invalidate_grid()

    def shortest_path(self, u, v, donotcross=True):
        """Return shortest path between u and v on the :attr:`grid`.

        Args:
            u (Point): The *from* Point geometry.
            v (Point): The *to* Point geometry.
            dotnotcross (bool): If true, this path will not be crossed by other paths.

        Returns:
            (LineString): The path from u to v along the studio graph
        """
        shortest_path = nx.shortest_path(self.grid, (u.x, u.y), (v.x, v.y))
        if donotcross:
            edges = self.grid.edges(shortest_path)
            for edge in edges:
                self.grid.remove_edges_from(edge)
        # create linestring and simplify to unit and return
        try:
            return LineString(shortest_path).simplify(1)
        except ValueError:
            return shortest_path
