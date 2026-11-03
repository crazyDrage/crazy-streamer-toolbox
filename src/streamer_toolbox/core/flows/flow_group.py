from dataclasses import dataclass

COLORS = ("blue", "teal", "green", "yellow", "orange", "red", "purple", "grey")


@dataclass(frozen=True)
class FlowGroup:
    """A coloured area with a name on the box view, behind the boxes (his round 83). The boxes whose middle is
    inside it belong to it: they move with it, and folded it shows as one small box. Only a view: it changes
    nothing in how the flow runs."""

    id: str
    label: str = "Group"
    color: str = "blue"
    box: tuple[float, float] = (0.0, 0.0)    # top left, in the box view
    size: tuple[float, float] = (420.0, 280.0)
    folded: bool = False

    def holds(self, spot: tuple[float, float]) -> bool:
        """Whether a point (a box's middle) is inside the open area."""
        x, y = spot
        return self.box[0] <= x <= self.box[0] + self.size[0] and self.box[1] <= y <= self.box[1] + self.size[1]
