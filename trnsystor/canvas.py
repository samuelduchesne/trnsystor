"""StudioCanvas module."""
from collections import deque
from shapely.errors import GEOSException
from shapely.geometry import LineString, box


class StudioCanvas:
    """StudioCanvas class.

    Handles geometric positioning of Components on a grid.
    The grid is represented implicitly and expanded on-demand when
    searching for paths.  This avoids constructing a full NetworkX grid
    graph which can easily reach millions of nodes for large canvases.
    """

    def __init__(self, width=2000, height=1000, step=1):
        """Initialize object.

        Args:
            width (int): The width of the grid in points.
            height (int): The height of the grid in points.
            step (int): Resolution of the grid in points.
        """
        self.width = width
        self.height = height
        self.step = step
        # Keep track of edges that should not be crossed by subsequent
        # paths.  Edges are stored as sorted tuples of coordinate pairs.
        self._blocked_edges = set()

    @property
    def bbox(self):
        """Return a bounding box rectangle for the canvas."""
        return box(0, 0, self.width, self.height)

    def invalidate_grid(self):
        """Reset cached path information."""
        self._blocked_edges.clear()

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

    def _neighbors(self, node):
        """Yield neighbouring nodes, honoring blocked edges."""
        x, y = node
        step = self.step
        candidates = [
            (x + step, y),
            (x - step, y),
            (x, y + step),
            (x, y - step),
        ]
        for nx_, ny in candidates:
            if 0 <= nx_ <= self.width and 0 <= ny <= self.height:
                edge = tuple(sorted((node, (nx_, ny))))
                if edge not in self._blocked_edges:
                    yield (nx_, ny)

    def shortest_path(self, u, v, donotcross=True):
        """Return shortest path between ``u`` and ``v``.

        The search is performed on-demand without constructing a full grid
        graph.  Only nodes that are explored during the breadth-first
        search are instantiated.

        Args:
            u (Point): The *from* Point geometry.
            v (Point): The *to* Point geometry.
            donotcross (bool): If true, this path will not be crossed by
                other paths (edges are blocked for subsequent searches).

        Returns:
            LineString: The path from ``u`` to ``v`` along the studio
            graph or ``None`` if no path exists.
        """
        start = (u.x, u.y)
        goal = (v.x, v.y)

        queue = deque([start])
        came_from = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            for nbr in self._neighbors(current):
                if nbr not in came_from:
                    queue.append(nbr)
                    came_from[nbr] = current

        if goal not in came_from:
            return None

        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()

        if donotcross:
            for edge in zip(path, path[1:]):
                self._blocked_edges.add(tuple(sorted(edge)))

        try:
            return LineString(path)
        except (ValueError, GEOSException):
            return path
