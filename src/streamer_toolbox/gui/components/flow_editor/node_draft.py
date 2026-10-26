from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.flows.flow_node import FlowNode


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

    @classmethod
    def from_node(cls, node: FlowNode) -> "NodeDraft":
        return cls(node.id, node.action, dict(node.params), node.enabled, node.note, node.save_as, node.box,
                   dict(node.outputs))

    def to_node(self) -> FlowNode:
        params = {k: v for k, v in self.params.items() if v not in ("", None)}
        return FlowNode(self.id, self.action, params, self.enabled, self.note.strip(), self.save_as.strip(),
                        self.box, dict(self.outputs))
