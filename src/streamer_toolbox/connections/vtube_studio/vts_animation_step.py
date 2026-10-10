from dataclasses import dataclass
from typing import Any

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition


@dataclass(frozen=True)
class VtsAnimationStep:
    """One step of a model animation: where to go (a spot, or a change from where the model started), how many
    seconds the way there takes, and how long to stay there before the next step."""

    position: VtsPosition
    seconds: float = 1.0
    wait: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VtsAnimationStep":
        return cls(VtsPosition.from_dict(data), max(0.0, float(data.get("seconds", 1.0))),
                   max(0.0, float(data.get("wait", 0.0))))

    def to_dict(self) -> dict[str, float]:
        return {**{k: round(v, 4) for k, v in self.position.to_dict().items()},
                "seconds": self.seconds, "wait": self.wait}
