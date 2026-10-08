from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.actions.registered_action import RegisteredAction

GENERAL = "General"  # the sub group of a box that has none


@dataclass(frozen=True)
class BoxFilter:
    """A named pick of what the Add box window shows: whole categories ("obs"), single sub groups of one
    ("obs/Media") and single boxes ("obs.play_video_once"), minus the boxes in `without` (taken out of a
    category or group that is in as a whole). So a long list becomes the handful of boxes he uses for one job,
    and a whole category still takes in boxes that come later."""

    name: str
    parts: tuple[str, ...] = field(default_factory=tuple)
    without: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoxFilter":
        return cls(str(data["name"]), tuple(str(p) for p in data.get("parts", [])),
                   tuple(str(p) for p in data.get("without", [])))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name, "parts": list(self.parts)}
        if self.without:
            data["without"] = list(self.without)
        return data

    def fits(self, action: RegisteredAction) -> bool:
        if action.name in self.without:
            return False
        return action.category in self.parts or part_of(action) in self.parts or action.name in self.parts


def part_of(action: RegisteredAction) -> str:
    """The filter part for one box's sub group: "obs/Media"."""
    return f"{action.category}/{action.group or GENERAL}"
