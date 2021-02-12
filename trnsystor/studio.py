"""StudioHeader module."""
from shapely.geometry import Point


class StudioHeader(object):
    """StudioHeader class.

    Each TrnsysModel has a StudioHeader which handles the studio comments
    such as position, UNIT_NAME, model, POSITION, LAYER, LINK_STYLE
    """

    def __init__(self, unit_name, model, position, layer=None):
        """Initialize object.

        Args:
            unit_name (str): The unit_name, eg.: "Type104".
            model (Path): The path of the tmf/xml file.
            position (Point, optional): The Point containing coordinates on the
                canvas.
            layer (list, optional): list of layer names on which the model is
                placed. Defaults to "Main".
        """
        if layer is None:
            layer = ["Main"]
        self.layer = layer
        self.position = position
        self.model = model
        self.unit_name = unit_name
        self.link_styles = {}

    def __str__(self):
        """Return deck representation of self."""
        return self._to_deck()

    @classmethod
    def from_component(cls, model):
        """Create object from :class:`TrnsysModel`."""
        position = Point(50, 50)
        layer = ["Main"]
        return cls(model.name, model.model, position, layer)

    def _to_deck(self):
        """Return deck representation of self."""
        unit_name = "*$UNIT_NAME {}".format(self.unit_name)
        model = "*$MODEL {}".format(self.model.expand())
        position = "*$POSITION {} {}".format(self.position.x, self.position.y)
        layer = "*$LAYER {}".format(" ".join(self.layer))
        return "\n".join([unit_name, model, position, layer]) + "\n"
