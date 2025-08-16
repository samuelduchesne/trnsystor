"""StudioCanvas module."""
from collections import deque
from shapely.geometry import LineString, box


class StudioCanvas:
    """StudioCanvas class.

    Handles geometric positioning of Components on a grid. Uses an implicit
    Manhattan grid with a configurable resolution instead of building the full
    grid up-front with :mod:`networkx`.
    """

    def __init__(self, width=2000, height=1000, step=1):
        """Initialize object.

        Args:
            width (int): The width of the grid in points.
            height (int): The height of the grid in points.
            step (int): Spacing between adjacent grid nodes in points.
        """
        self.width = width
        self.height = height
        self.step = step
        self._blocked_edges = set()

    @property
    def bbox(self):
        """Return a bounding box rectangle for the canvas."""
        return box(0, 0, self.width, self.height)

    def invalidate_grid(self):
        """Clear all blocked edges so paths may be recomputed."""
        self._blocked_edges.clear()

    def resize_canvas(self, width, height, step=None):
        """Change the canvas size and optionally the grid resolution.

        TODO: Handle grid when canvas size is changed (e.g used paths)

        Args:
            width (int): new width.
            height (int): new height.
            step (int, optional): new grid step size.
        """
        self.width = width
        self.height = height
        if step is not None:
            self.step = step
        self.invalidate_grid()

    def _neighbors(self, node):
        x, y = node
        s = self.step
        if x - s >= 0:
            yield (x - s, y)
        if x + s <= self.width:
            yield (x + s, y)
        if y - s >= 0:
            yield (x, y - s)
        if y + s <= self.height:
            yield (x, y + s)

    def _edge_key(self, a, b):
        return frozenset((a, b))

    def _edge_blocked(self, a, b):
        return self._edge_key(a, b) in self._blocked_edges

    def shortest_path(self, u, v, donotcross=True):
        """Return shortest path between u and v on the implicit grid.

        Args:
            u (Point): The *from* Point geometry.
            v (Point): The *to* Point geometry.
            donotcross (bool): If true, this path will not be crossed by other
                paths.

        Returns:
            LineString: The path from ``u`` to ``v`` along the studio graph.
        """
        start = (int(u.x), int(u.y))
        goal = (int(v.x), int(v.y))

        queue = deque([start])
        parents = {start: None}

        while queue:
            node = queue.popleft()
            if node == goal:
                break
            for nbr in self._neighbors(node):
                if nbr in parents or self._edge_blocked(node, nbr):
                    continue
                parents[nbr] = node
                queue.append(nbr)

        if goal not in parents:
            path = [start, goal]
        else:
            path = [goal]
            while parents[path[-1]] is not None:
                path.append(parents[path[-1]])
            path.reverse()

        if donotcross and len(path) > 1:
            for a, b in zip(path, path[1:]):
                self._blocked_edges.add(self._edge_key(a, b))

        if len(path) < 2:
            path = path * 2  # duplicate single coordinate for LineString
        try:
            return LineString(path)
        except ValueError:
            return path
