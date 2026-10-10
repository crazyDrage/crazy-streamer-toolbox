from dataclasses import dataclass, replace
from typing import Any

from streamer_toolbox.connections.vtube_studio.vts_animation_step import VtsAnimationStep
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition


@dataclass(frozen=True)
class VtsAnimation:
    """A model animation: steps played one after the other.

    Fixed: each step is a spot on the screen. Relative: each step is a change from where the model is when the
    animation starts (x +0.1 = a bit right of there), so it plays the same shape anywhere. `base` is the spot the
    changes were measured from while editing (to record and to draw them); playing doesn't use it.
    as_relative / as_fixed switch between the two and calculate the steps over."""

    steps: tuple[VtsAnimationStep, ...] = ()
    relative: bool = False
    base: VtsPosition | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "VtsAnimation":
        """From what the box keeps ({"relative": .., "base": {..}, "steps": [..]}); empty = no steps."""
        if data in (None, ""):
            return cls()
        if not isinstance(data, dict):
            raise TypeError(f"an animation needs steps, got {data!r}")
        base = data.get("base")
        return cls(tuple(VtsAnimationStep.from_dict(s) for s in data.get("steps", [])),
                   bool(data.get("relative", False)), VtsPosition.from_dict(base) if base else None)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"relative": self.relative, "steps": [s.to_dict() for s in self.steps]}
        if self.base:
            data["base"] = {k: round(v, 4) for k, v in self.base.to_dict().items()}
        return data

    @property
    def seconds(self) -> float:
        """How long one play takes."""
        return sum(s.seconds + s.wait for s in self.steps)

    def target(self, step: VtsAnimationStep, start: VtsPosition) -> VtsPosition:
        """Where a step goes when the animation started at `start`."""
        return start.plus(step.position) if self.relative else step.position

    def as_relative(self, base: VtsPosition) -> "VtsAnimation":
        """Each spot as the change from base (often step 1, so the animation starts where the model is)."""
        if self.relative:
            return self
        return VtsAnimation(tuple(replace(s, position=s.position.minus(base)) for s in self.steps), True, base)

    def as_fixed(self, base: VtsPosition) -> "VtsAnimation":
        """Each change as the spot it reaches from base (e.g. where the model is now)."""
        if not self.relative:
            return self
        return VtsAnimation(tuple(replace(s, position=base.plus(s.position)) for s in self.steps), False, None)
