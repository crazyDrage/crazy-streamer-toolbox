from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from streamer_toolbox.core.actions.numbered_fields import count_field, numbered_fields
from streamer_toolbox.core.flows.box_wire import BOX_REF, WIRE_IN, box_ref, box_source
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_group import FlowGroup
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import INPUT, START, FlowWire
from streamer_toolbox.core.flows.frozen_box import FrozenBox
from streamer_toolbox.core.flows.old_start_box import start_boxes_from_triggers
from streamer_toolbox.core.flows.start_boxes import first_wires, free_trigger_id, new_flow
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


@dataclass
class FlowDraft:
    """A flow while it's being edited: boxes, wires, inputs, triggers. Inputs, triggers and wires are frozen
    values and replaced whole. The list view edits the graph through add_after / add_beside / remove. Each
    trigger is a Start box (its id); start_box / input_box are where Manual Start and Input sit."""

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
    enabled: bool = True
    triggers_enabled: bool = True
    as_box: bool = True
    start_box: tuple[float, float] | None = None
    input_box: tuple[float, float] | None = None
    hidden: bool = False
    groups: list[FlowGroup] = field(default_factory=list)  # coloured areas on the canvas (his round 83)
    # the named lines of a box (NodeEditor sets it from the box's action): kept on save even when empty
    named_lines: Callable[[NodeDraft], list[str]] = field(default=lambda node: [], repr=False, compare=False)

    @classmethod
    def from_flow(cls, flow: Flow) -> "FlowDraft":
        if any(not t.id for t in flow.triggers):  # made in code, not read from a file: each trigger its Start box
            flow = replace(flow, **dict(zip(("nodes", "wires", "triggers"), start_boxes_from_triggers(
                flow.nodes, flow.wires, flow.triggers, flow.inputs))))
        return cls(flow.name, flow.label, flow.description, [NodeDraft.from_node(n) for n in flow.nodes],
                   list(flow.wires), list(flow.inputs), list(flow.triggers), flow.when_busy, flow.cooldown,
                   flow.user_cooldown, flow.refund_on_fail, flow.folder, flow.enabled, flow.triggers_enabled,
                   flow.as_box, flow.start_box, flow.input_box, flow.hidden, list(flow.groups))

    @classmethod
    def new(cls) -> "FlowDraft":
        """A new flow: Start wired to its End box (his round 63)."""
        return cls.from_flow(new_flow("", "New flow"))

    def to_flow(self) -> Flow:
        ids = {n.id for n in self.nodes} | {START, INPUT} | {t.id for t in self.triggers}
        for node in self.nodes:  # a field wired to a deleted box waits for a new wire
            for key, value in node.params.items():
                source = box_source(value)
                if source and source[0] not in ids:
                    node.params[key] = WIRE_IN
        wires = tuple(dict.fromkeys(w for w in self.wires if w.source in ids and w.target in ids))
        return Flow(self.name, self.label.strip() or self.name, tuple(n.to_node(self.named_lines(n)) for n in self.nodes), wires,
                    tuple(self.triggers), self.description.strip(), tuple(self.inputs), self.when_busy,
                    float(self.cooldown or 0), float(self.user_cooldown or 0), self.refund_on_fail,
                    self.folder.strip(), self.enabled, self.triggers_enabled, self.as_box, self.start_box,
                    self.input_box, self.hidden, tuple(self.groups))

    def add_group(self, spot: tuple[float, float]) -> FlowGroup:
        numbers = [int(g.id[1:]) for g in self.groups if g.id[:1] == "g" and g.id[1:].isdigit()]
        group = FlowGroup(f"g{max(numbers, default=0) + 1}", box=spot)
        self.groups.append(group)
        return group

    def group(self, group_id: str) -> FlowGroup | None:
        return next((g for g in self.groups if g.id == group_id), None)

    def trigger(self, node_id: str) -> FlowTrigger | None:
        return next((t for t in self.triggers if t.id == node_id), None)

    def add_trigger(self, trigger: FlowTrigger) -> FlowTrigger:
        """One more trigger, as its own Start box wired like the Manual Start (a new flow's: into End)."""
        trigger = replace(trigger, id=free_trigger_id([t.id for t in self.triggers]))
        self.triggers.append(trigger)
        self.wires += first_wires(trigger.id, self.wires)
        return trigger

    def remove_trigger(self, node_id: str) -> None:
        """Takes a trigger away with its Start box's wires; fields wired to its dots wait for a new wire."""
        self.triggers = [t for t in self.triggers if t.id != node_id]
        self.wires = [w for w in self.wires if w.source != node_id]

    def set_trigger(self, node_id: str, **changes) -> None:
        """Changes a trigger (kind, match), keeping its Start box."""
        self.triggers = [replace(t, **changes) if t.id == node_id else t for t in self.triggers]

    def node(self, node_id: str) -> NodeDraft | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def refuses(self, action: RegisteredAction | None) -> str:
        """Why a box of this action can't be added here ("" = it can): a once_per_flow box (End) that the flow
        has already (his round 55)."""
        if action and action.once_per_flow and any(n.action == action.name for n in self.nodes):
            more = ": give it more values instead (+ Add value)" if action.named_lines else ""
            return f"This flow has its {action.title} box already" + more
        return ""

    def new_node(self, action: str) -> NodeDraft:
        numbers = [int(n.id[1:]) for n in self.nodes if n.id[:1] == "n" and n.id[1:].isdigit()]
        node = NodeDraft(f"n{max(numbers, default=0) + 1}", action)
        self.nodes.append(node)
        return node

    def add_copy(self, original: NodeDraft, same_flow: bool) -> NodeDraft:
        """A copy of a box as a new, unwired box, a bit right of and below the original's spot. Its orange wires
        stay when it comes from this flow (it reads the same boxes); from another flow they wait for a new wire,
        because box numbers there mean other boxes."""
        return self.add_copies([original], [], same_flow)[0]

    def add_copies(self, originals: list[NodeDraft], wires: list[FlowWire], same_flow: bool,
                   spot: tuple[float, float] | None = None) -> list[NodeDraft]:
        """Copies of several boxes at once (his round 83), like add_copy: the wires among them (run and orange)
        lead between the copies, so the group works on its own. spot: where the top left one goes (the others
        keep their places around it); without one they sit a bit right of and below the originals."""
        new_ids = {original.id: self.new_node(original.action).id for original in originals}
        spots = [o.box for o in originals if o.box is not None]
        corner = (min(x for x, _ in spots), min(y for _, y in spots)) if spots else (0.0, 0.0)
        made = []
        for original in originals:
            node = self.node(new_ids[original.id])
            node.params = {k: _copied(v, new_ids, same_flow) for k, v in original.params.items()}
            node.enabled, node.note, node.save_as = original.enabled, original.note, original.save_as
            node.outputs = dict(original.outputs)
            if original.box is not None:
                x, y = original.box
                node.box = (spot[0] + x - corner[0], spot[1] + y - corner[1]) if spot else (x + 40, y + 60)
            elif spot is not None:
                node.box = spot
            made.append(node)
        self.wires += [FlowWire(new_ids[w.source], w.port, new_ids[w.target], w.entry) for w in wires
                       if w.source in new_ids and w.target in new_ids]
        return made

    def add_after(self, source: str, port: str, action: str, first_port: str) -> NodeDraft:
        """A new box right after source's port; what came after it now comes after the new box. Right after a
        Start box it also goes after the other Start boxes wired the same way (a new flow's all lead into End),
        so a box added for Start runs for every trigger too."""
        node = self.new_node(action)
        moved = [w for w in self.wires if w.source == source and w.port == port]
        sources = [source]
        if source in {START, *(t.id for t in self.triggers)}:
            after = self._after_start(source)
            sources += [t.id for t in self.triggers if t.id != source and self._after_start(t.id) == after]
            sources += [START] if source != START and self._after_start(START) == after else []
        self.wires = [w for w in self.wires if w not in moved and not (w.source in sources[1:] and w.port == port)]
        self.wires += [FlowWire(s, port, node.id) for s in sources]
        self.wires += [FlowWire(node.id, first_port, w.target, w.entry) for w in moved]
        return node

    def _after_start(self, start: str) -> set[tuple[str, str]]:
        return {(w.target, w.entry) for w in self.wires if w.source == start}

    def add_beside(self, node_id: str, action: str) -> NodeDraft:
        """A new box that starts at the same time as node_id (same wires in)."""
        node = self.new_node(action)
        self.wires += [FlowWire(w.source, w.port, node.id) for w in self.wires if w.target == node_id and not w.entry]
        return node

    def remove_numbered(self, node_id: str, prefix: str, number: int) -> None:
        """Takes one numbered field out of a box (a Switch's case_2, also its output; a Choose value's value_2, also
        its run dot): the ones after it move up one number, with their wires; the wires from or into the removed
        one go. The last one stays."""
        node = self.node(node_id)
        names = numbered_fields(prefix, node.params) if node else []
        if len(names) <= 1 or not 1 <= number <= len(names):
            return
        values = [node.params.pop(name, "") for name in names]
        del values[number - 1]
        node.params.update(zip(names, values))
        node.params[count_field(prefix)] = len(values)
        moved = {names[i]: names[i - 1] for i in range(number, len(names))}  # case_3 -> case_2, ...
        gone = names[number - 1]
        self.wires = [FlowWire(w.source, moved.get(w.port, w.port) if w.source == node_id else w.port, w.target,
                               moved.get(w.entry, w.entry) if w.target == node_id else w.entry)
                      for w in self.wires
                      if not (w.source == node_id and w.port == gone or w.target == node_id and w.entry == gone)]

    def move_numbered(self, node_id: str, prefix: str, number: int, step: int) -> None:
        """Moves one numbered field up (step -1) or down (+1) by trading places with its neighbour (his round 59):
        their values and their wires (a Switch case's output, a Choose value line's run dot) trade too."""
        node = self.node(node_id)
        names = numbered_fields(prefix, node.params) if node else []
        if not (1 <= number <= len(names) and 1 <= number + step <= len(names)) or step == 0:
            return
        this, other = names[number - 1], names[number - 1 + step]
        values = {name: node.params.pop(name) for name in (this, other) if name in node.params}
        node.params.update({other if name == this else this: value for name, value in values.items()})
        traded = {this: other, other: this}
        self.wires = [FlowWire(w.source, traded.get(w.port, w.port) if w.source == node_id else w.port, w.target,
                               traded.get(w.entry, w.entry) if w.target == node_id else w.entry)
                      for w in self.wires]

    def rename_output(self, node_id: str, old: str, new: str) -> None:
        """A Value box's line renamed: the fields wired to it follow (${box.n3.old} → ${box.n3.new}). new = "" (the
        line taken away): those fields wait for a new wire."""
        for node in self.nodes:
            for key, value in node.params.items():
                source = box_source(value)
                if source and source[0] == node_id and (source[1] == old or source[1].startswith(old + ".")):
                    node.params[key] = box_ref(node_id, new + source[1][len(old):]) if new else WIRE_IN

    def freeze(self, node_id: str, value: Any, at: str) -> None:
        """Freezes a box with what it gave (his idea of 10-29): its run wires are kept on it, hidden, and the boxes
        before it lead to the ones after it; Run again on a frozen box only keeps the new value."""
        node = self.node(node_id)
        if node.frozen is not None:
            node.frozen = replace(node.frozen, value=value, at=at)
            return
        hidden = tuple(w for w in self.wires if node_id in (w.source, w.target))
        old = list(self.wires)
        self.take_off_run_wires(node_id)
        node.frozen = FrozenBox(value, at, hidden, tuple(w for w in self.wires if w not in old))

    def unfreeze(self, node_id: str) -> None:
        """Back to a normal box: the wires added around it go, its own come back (those whose other end is still
        there)."""
        node = self.node(node_id)
        if node is None or node.frozen is None:
            return
        ids = {n.id for n in self.nodes} | {START, INPUT} | {t.id for t in self.triggers}
        self.wires = [w for w in self.wires if w not in node.frozen.bridged]
        self.wires += [w for w in node.frozen.wires if w.source in ids and w.target in ids and w not in self.wires]
        node.frozen = None

    def take_off_run_wires(self, node_id: str) -> None:
        """A box that only gives values sat in the run chain (a flow from before it was one): the boxes before it
        now lead to the ones after it, and it keeps only its data wires."""
        incoming = [w for w in self.wires if w.target == node_id and not w.entry]
        outgoing = [(w.target, w.entry) for w in self.wires if w.source == node_id]
        self.wires = [w for w in self.wires if node_id not in (w.source, w.target)]
        self.wires += [FlowWire(w.source, w.port, t, e) for w in incoming for t, e in outgoing
                       if FlowWire(w.source, w.port, t, e) not in self.wires]

    def remove(self, node_id: str, ports: tuple[str, ...]) -> None:
        """Deletes a box. A box with one output is bridged: what led into it now leads to what came after."""
        incoming = [w for w in self.wires if w.target == node_id and not w.entry]
        outgoing = [(w.target, w.entry) for w in self.wires if w.source == node_id]
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.wires = [w for w in self.wires if node_id not in (w.source, w.target)]
        if len(ports) == 1:
            self.wires += [FlowWire(w.source, w.port, t, e) for w in incoming for t, e in outgoing
                           if FlowWire(w.source, w.port, t, e) not in self.wires]


def _copied(value: Any, new_ids: dict[str, str], same_flow: bool) -> Any:
    """A field of a copied box: a wire to a box copied with it leads to that copy; to another box it stays in
    the same flow and waits for a new wire in another one. ${box.n3.user} inside a text follows its copy too."""
    source = box_source(value)
    if source:
        if source[0] in new_ids:
            return box_ref(new_ids[source[0]], source[1])
        return value if same_flow else WIRE_IN
    if isinstance(value, str):
        return BOX_REF.sub(lambda m: m.group(0).replace(f"box.{m.group(1)}", f"box.{new_ids[m.group(1)]}", 1)
                           if m.group(1) in new_ids else m.group(0), value)
    return value
