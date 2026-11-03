import copy

from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class BoxClipboard:
    """The boxes last copied (Copy, Ctrl+C) for Paste (Ctrl+V), also into another flow or on another device: one
    for the whole toolbox, there's one streamer. One box or several (his round 83), with the wires among them.
    Keeps a snapshot, so editing the boxes afterwards doesn't change it."""

    def __init__(self) -> None:
        self._boxes: list[NodeDraft] = []
        self._wires: list[FlowWire] = []
        self._flow = ""

    @property
    def has_box(self) -> bool:
        return bool(self._boxes)

    def copy(self, nodes: list[NodeDraft], flow: str, wires: list[FlowWire] | None = None) -> None:
        ids = {n.id for n in nodes}
        self._boxes = copy.deepcopy(nodes)
        self._wires = [w for w in wires or [] if w.source in ids and w.target in ids]
        self._flow = flow

    def take(self, flow: str) -> tuple[list[NodeDraft], list[FlowWire], bool] | None:
        """Fresh copies of the boxes, the wires among them and whether they come from this same flow (their
        orange wires to other boxes still fit)."""
        if not self._boxes:
            return None
        return copy.deepcopy(self._boxes), list(self._wires), bool(flow) and flow == self._flow


CLIPBOARD = BoxClipboard()
