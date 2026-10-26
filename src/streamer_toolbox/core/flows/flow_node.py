from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FlowNode:
    """One box in a flow: run `action` with `params`.

    Text in params may use ${var.name} / ${var.name.field} (variables), ${input.name} (the flow's inputs) and
    ${event.key} (what triggered it); a value that is only a placeholder keeps its type (a position stays an
    object). `save_as` stores what the action returns in that variable. A switched-off box is skipped, but the
    boxes after it still run. `box` is where it sits in the box view (x, y). `outputs` = data dots of this one box
    ({key: kind}), from its last result (his round 60: per box, not a new box) or what's wired into it.
    """

    id: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    note: str = ""
    save_as: str = ""
    box: tuple[float, float] | None = None
    outputs: dict[str, str] = field(default_factory=dict)
