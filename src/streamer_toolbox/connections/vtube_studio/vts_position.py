from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VtsPosition:
    """Where the model sits in VTube Studio: x/y from -1 to 1 (screen edges), rotation in degrees, size -100..100.

    The same four numbers also serve as a change (an animation step relative to where the model started):
    plus() adds one, minus() gives the change from another position to this one."""

    x: float
    y: float
    rotation: float
    size: float

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "VtsPosition":
        """From VTS's modelPosition (or SAMMI's saved copy of it)."""
        return cls(float(data["positionX"]), float(data["positionY"]), float(data["rotation"]), float(data["size"]))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VtsPosition":
        """From {x, y, rotation, size} (what Get model position saves in a variable)."""
        if not isinstance(data, dict):
            raise TypeError(f"a position needs x, y, rotation and size, got {data!r}")
        return cls(float(data["x"]), float(data["y"]), float(data["rotation"]), float(data["size"]))

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "rotation": self.rotation, "size": self.size}

    def to_api(self) -> dict[str, float]:
        return {"positionX": self.x, "positionY": self.y, "rotation": self.rotation, "size": self.size}

    def plus(self, change: "VtsPosition") -> "VtsPosition":
        return VtsPosition(self.x + change.x, self.y + change.y, _turn(self.rotation + change.rotation),
                           self.size + change.size)

    def minus(self, other: "VtsPosition") -> "VtsPosition":
        """The change from other to this one; the rotation the short way round (350° → 10° = +20°)."""
        return VtsPosition(self.x - other.x, self.y - other.y, _turn(self.rotation - other.rotation),
                           self.size - other.size)

    def towards(self, other: "VtsPosition", part: float) -> "VtsPosition":
        """The point part of the way (0..1) from here to other, turning the short way round."""
        change = other.minus(self)
        return VtsPosition(self.x + change.x * part, self.y + change.y * part,
                           _turn(self.rotation + change.rotation * part), self.size + change.size * part)

    def turned_near(self, rotation: float) -> "VtsPosition":
        """The same position with its rotation written as close to `rotation` as possible (VTS takes -360..360,
        10° and -350° are the same), so a move from -10° to 350° doesn't turn all the way round. (From 360° to 10°
        VTS itself takes the short way: seen on the real VTS, 2026-10-01.)"""
        options = [r for r in (self.rotation - 360, self.rotation, self.rotation + 360) if -360 <= r <= 360]
        return VtsPosition(self.x, self.y, min(options, key=lambda r: abs(r - rotation)), self.size)


def _turn(degrees: float) -> float:
    """An angle as -180..180."""
    degrees = (degrees + 180) % 360 - 180
    return 180.0 if degrees == -180 else degrees
