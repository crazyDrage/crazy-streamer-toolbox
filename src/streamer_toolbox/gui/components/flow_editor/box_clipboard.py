import copy

from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class BoxClipboard:
    """The box last copied (Copy, Ctrl+C) for Paste (Ctrl+V), also into another flow or on another device: one for
    the whole toolbox, there's one streamer. Keeps a snapshot, so editing the box afterwards doesn't change it."""

    def __init__(self) -> None:
        self._box: NodeDraft | None = None
        self._flow = ""

    @property
    def has_box(self) -> bool:
        return self._box is not None

    def copy(self, node: NodeDraft, flow: str) -> None:
        self._box = copy.deepcopy(node)
        self._flow = flow

    def take(self, flow: str) -> tuple[NodeDraft, bool] | None:
        """A fresh copy of the box and whether it comes from this same flow (its orange wires still fit)."""
        if self._box is None:
            return None
        return copy.deepcopy(self._box), bool(flow) and flow == self._flow


CLIPBOARD = BoxClipboard()
