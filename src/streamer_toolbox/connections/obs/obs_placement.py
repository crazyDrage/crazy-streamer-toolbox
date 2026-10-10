from dataclasses import dataclass
from typing import Any

from streamer_toolbox.core.data.box_value import to_kind

TOP_LEFT = 5  # OBS's alignment number for "the position is the top left corner"


@dataclass(frozen=True)
class ObsPlacement:
    """Where something sits in a scene: the spot (x / y of its anchor, in canvas pixels), the box it fills
    (width × height as shown), its turn and which corner the spot means. Taken from one source (a marker he
    dragged into place in OBS), given to another: that one is fitted into the box keeping its shape, whatever
    its own size is. `scene` only remembers where it was set up."""

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    alignment: int = TOP_LEFT
    scene: str = ""

    @classmethod
    def from_transform(cls, transform: dict[str, Any], scene: str = "") -> "ObsPlacement":
        """From OBS's sceneItemTransform: the box is its bounds if it has them, else the size it's shown at."""
        has_bounds = transform.get("boundsType", "OBS_BOUNDS_NONE") != "OBS_BOUNDS_NONE"
        width = transform.get("boundsWidth" if has_bounds else "width", 0)
        height = transform.get("boundsHeight" if has_bounds else "height", 0)
        return cls(round(float(transform.get("positionX", 0)), 2), round(float(transform.get("positionY", 0)), 2),
                   round(float(width), 2), round(float(height), 2), round(float(transform.get("rotation", 0)), 2),
                   int(transform.get("alignment", TOP_LEFT)), scene)

    @classmethod
    def from_value(cls, value: Any) -> "ObsPlacement":
        """From a box field: the object the place window keeps, the same as JSON text, or Get source place's
        result on a wire."""
        try:
            data = to_kind(value, "object")
            return cls(float(data["x"]), float(data["y"]), float(data.get("width", 0)), float(data.get("height", 0)),
                       float(data.get("rotation", 0)), int(data.get("alignment", TOP_LEFT)), str(data.get("scene", "")))
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"a place is an object like {{\"x\": 100, \"y\": 50, \"width\": 320, \"height\": 180}}, "
                             f"not {value!r}") from None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"x": self.x, "y": self.y, "width": self.width, "height": self.height,
                                "rotation": self.rotation, "alignment": self.alignment}
        if self.scene:
            data["scene"] = self.scene
        return data

    def to_transform(self) -> dict[str, Any]:
        """For SetSceneItemTransform: the spot, and the box as bounds the source is fitted into (no box for
        something without a size, like a sound)."""
        transform: dict[str, Any] = {"positionX": self.x, "positionY": self.y, "rotation": self.rotation,
                                     "alignment": self.alignment}
        if self.width > 0 and self.height > 0:
            transform |= {"boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0,
                          "boundsWidth": self.width, "boundsHeight": self.height}
        return transform

    def text(self) -> str:
        """"x 1600, y 50 · 320 × 180 · in toolbox_test"."""
        size = f" · {self.width:g} × {self.height:g}" if self.width > 0 and self.height > 0 else ""
        turn = f" · turned {self.rotation:g}°" if self.rotation else ""
        return f"x {self.x:g}, y {self.y:g}{size}{turn}" + (f" · set up in {self.scene}" if self.scene else "")
