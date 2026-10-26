from dataclasses import dataclass, field, replace

from streamer_toolbox.core.flows.box_wire import BOX_REF
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import START, FlowWire

END_ACTION = "logic.end"  # the End box; only old_end_boxes reads it by name (flows from before round 55)
END_LINE = "name"  # an End box's way out until round 55 (dropped when read, old_end_boxes); no value is called so


@dataclass(frozen=True)
class Flow:
    """A saved graph of boxes; becomes the action flow.<name> (a button on Live, in SAMMI, over the API). It has
    a Start box per way it starts (his round 63): Manual (id "start": button, API, another flow) and one per
    trigger (its id), and an Input box (id "input") whose orange dots are the inputs."""

    name: str
    label: str
    nodes: tuple[FlowNode, ...] = ()
    wires: tuple[FlowWire, ...] = ()
    triggers: tuple[FlowTrigger, ...] = field(default_factory=tuple)
    description: str = ""
    inputs: tuple[FlowInput, ...] = field(default_factory=tuple)
    when_busy: str = "alongside"  # started again while it runs: "alongside", "queue" (wait in line) or "skip"
    cooldown: float = 0           # seconds before a trigger may start it again (anyone)
    user_cooldown: float = 0      # seconds before the same viewer's trigger may start it again
    refund_on_fail: bool = False  # a redeem that started it gets its points back if it fails or is held back
    folder: str = ""              # where the Flows page lists it ("" = no folder); the file and action stay put
    enabled: bool = True          # off: it doesn't start at all (button, SAMMI, API, another flow, trigger)
    triggers_enabled: bool = True  # off: its triggers don't start it; its button and the others still do
    as_box: bool = True           # off: the Add box window doesn't offer it in other flows (his round 56)
    start_box: tuple[float, float] | None = None  # where the Manual Start box sits in the box view
    input_box: tuple[float, float] | None = None  # where the Input box sits

    def trigger(self, node_id: str) -> FlowTrigger | None:
        """The trigger whose Start box has this id."""
        return next((t for t in self.triggers if t.id and t.id == node_id), None)

    def without_triggers(self) -> "Flow":
        """A copy without its triggers and their Start boxes' wires (an imported or copied flow)."""
        return replace(self, triggers=(), wires=tuple(w for w in self.wires if self.trigger(w.source) is None))

    def starts(self) -> list[str]:
        """The ids of its Start boxes: Manual, then one per trigger."""
        return [START, *(t.id for t in self.triggers if t.id)]

    @property
    def action_name(self) -> str:
        return f"flow.{self.name}"

    def data_loop(self) -> list[str]:
        """Boxes whose orange wires go round (a needs b needs a): ["n3", "n5", "n3"], or [] if there is none.
        Such boxes can never get their value; run wires may loop, data wires may not (like LOGO!'s rule)."""
        needs = {n.id: [m.group(1) for v in n.params.values() if isinstance(v, str) for m in BOX_REF.finditer(v)
                        if self.node(m.group(1)) is not None]  # Start and deleted boxes can't be in a loop
                 for n in self.nodes}
        done: set[str] = set()

        def visit(node_id: str, path: list[str]) -> list[str]:
            if node_id in path:
                return path[path.index(node_id):] + [node_id]
            if node_id in done:
                return []
            for other in needs.get(node_id, []):
                loop = visit(other, path + [node_id])
                if loop:
                    return loop
            done.add(node_id)
            return []

        for node_id in needs:
            loop = visit(node_id, [])
            if loop:
                return loop
        return []

    def node(self, node_id: str) -> FlowNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def targets(self, source: str, port: str) -> list[str]:
        """The boxes the port runs (wires into their normal run dot)."""
        return [w.target for w in self.wires if w.source == source and w.port == port and not w.entry]

    def entries(self, source: str, port: str) -> list[tuple[str, str]]:
        """(box, entry) for the wires from the port into a box's extra run dot (a Loop's stop)."""
        return [(w.target, w.entry) for w in self.wires if w.source == source and w.port == port and w.entry]

