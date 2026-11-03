from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.frozen_box import FrozenBox


@dataclass
class NodeDraft:
    """A box while it's being edited (FlowNode is frozen)."""

    id: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    note: str = ""
    save_as: str = ""
    box: tuple[float, float] | None = None
    outputs: dict[str, str] = field(default_factory=dict)
    frozen: FrozenBox | None = None

    @classmethod
    def from_node(cls, node: FlowNode) -> "NodeDraft":
        return cls(node.id, node.action, dict(node.params), node.enabled, node.note, node.save_as, node.box,
                   dict(node.outputs), node.frozen)

    def to_node(self, keep: Collection[str] = ()) -> FlowNode:
        """An empty field is left out (its default counts), except the ones in keep: the lines he named or got
        (his round 81: a box's lines stay even when empty, or it gets confusing later)."""
        params = {k: v for k, v in self.params.items() if v not in ("", None) or k in keep}
        return FlowNode(self.id, self.action, params, self.enabled, self.note.strip(), self.save_as.strip(),
                        self.box, dict(self.outputs), self.frozen)
