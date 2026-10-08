from dataclasses import dataclass, field

from streamer_toolbox.core.actions.numbered_fields import count_field, numbered_fields
from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_source
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


@dataclass
class FlowDraft:
    """A flow while it's being edited: boxes, wires, inputs, triggers. Inputs, triggers and wires are frozen
    values and replaced whole. The list view edits the graph through add_after / add_beside / remove."""

    name: str
    label: str
    description: str = ""
    nodes: list[NodeDraft] = field(default_factory=list)
    wires: list[FlowWire] = field(default_factory=list)
    inputs: list[FlowInput] = field(default_factory=list)
    triggers: list[FlowTrigger] = field(default_factory=list)
    when_busy: str = "alongside"
    cooldown: float = 0
    user_cooldown: float = 0
    refund_on_fail: bool = False
    folder: str = ""

    @classmethod
    def from_flow(cls, flow: Flow) -> "FlowDraft":
        return cls(flow.name, flow.label, flow.description, [NodeDraft.from_node(n) for n in flow.nodes],
                   list(flow.wires), list(flow.inputs), list(flow.triggers), flow.when_busy, flow.cooldown,
                   flow.user_cooldown, flow.refund_on_fail, flow.folder)

    def to_flow(self) -> Flow:
        ids = {n.id for n in self.nodes} | {"start"}
        for node in self.nodes:  # a field wired to a deleted box waits for a new wire
            for key, value in node.params.items():
                source = box_source(value)
                if source and source[0] not in ids:
                    node.params[key] = WIRE_IN
        wires = tuple(dict.fromkeys(w for w in self.wires if w.source in ids and w.target in ids))
        return Flow(self.name, self.label.strip() or self.name, tuple(n.to_node() for n in self.nodes), wires,
                    tuple(self.triggers), self.description.strip(), tuple(self.inputs), self.when_busy,
                    float(self.cooldown or 0), float(self.user_cooldown or 0), self.refund_on_fail,
                    self.folder.strip())

    def node(self, node_id: str) -> NodeDraft | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def new_node(self, action: str) -> NodeDraft:
        numbers = [int(n.id[1:]) for n in self.nodes if n.id[:1] == "n" and n.id[1:].isdigit()]
        node = NodeDraft(f"n{max(numbers, default=0) + 1}", action)
        self.nodes.append(node)
        return node

    def add_copy(self, original: NodeDraft, same_flow: bool) -> NodeDraft:
        """A copy of a box as a new, unwired box, a bit right of and below the original's spot. Its orange wires
        stay when it comes from this flow (it reads the same boxes); from another flow they wait for a new wire,
        because box numbers there mean other boxes."""
        node = self.new_node(original.action)
        node.params = {k: (v if same_flow or not box_source(v) else WIRE_IN) for k, v in original.params.items()}
        node.enabled, node.note, node.save_as = original.enabled, original.note, original.save_as
        if original.box is not None:
            node.box = (original.box[0] + 40, original.box[1] + 60)
        return node

    def add_after(self, source: str, port: str, action: str, first_port: str) -> NodeDraft:
        """A new box right after source's port; what came after it now comes after the new box."""
        node = self.new_node(action)
        moved = [w for w in self.wires if w.source == source and w.port == port]
        self.wires = [w for w in self.wires if w not in moved]
        self.wires.append(FlowWire(source, port, node.id))
        self.wires += [FlowWire(node.id, first_port, w.target, w.entry) for w in moved]
        return node

    def add_beside(self, node_id: str, action: str) -> NodeDraft:
        """A new box that starts at the same time as node_id (same wires in)."""
        node = self.new_node(action)
        self.wires += [FlowWire(w.source, w.port, node.id) for w in self.wires if w.target == node_id and not w.entry]
        return node

    def remove_numbered(self, node_id: str, prefix: str, number: int) -> None:
        """Takes one numbered field out of a box (a Switch's case_2, also its output): the ones after it move up
        one number, with their wires; the wires from the removed one go. The last one stays."""
        node = self.node(node_id)
        names = numbered_fields(prefix, node.params) if node else []
        if len(names) <= 1 or not 1 <= number <= len(names):
            return
        values = [node.params.pop(name, "") for name in names]
        del values[number - 1]
        node.params.update(zip(names, values))
        node.params[count_field(prefix)] = len(values)
        moved = {names[i]: names[i - 1] for i in range(number, len(names))}  # case_3 -> case_2, ...
        self.wires = [FlowWire(w.source, moved.get(w.port, w.port) if w.source == node_id else w.port, w.target,
                               w.entry)
                      for w in self.wires if not (w.source == node_id and w.port == names[number - 1])]

    def remove(self, node_id: str, ports: tuple[str, ...]) -> None:
        """Deletes a box. A box with one output is bridged: what led into it now leads to what came after."""
        incoming = [w for w in self.wires if w.target == node_id and not w.entry]
        outgoing = [(w.target, w.entry) for w in self.wires if w.source == node_id]
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.wires = [w for w in self.wires if node_id not in (w.source, w.target)]
        if len(ports) == 1:
            self.wires += [FlowWire(w.source, w.port, t, e) for w in incoming for t, e in outgoing
                           if FlowWire(w.source, w.port, t, e) not in self.wires]
