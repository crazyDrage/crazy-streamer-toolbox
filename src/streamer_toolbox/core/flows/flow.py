from dataclasses import dataclass, field

from streamer_toolbox.core.flows.box_wire import BOX_REF
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire

OUTPUT_ACTION = "logic.output"  # a Flow output box: what the flow gives back when it's used as a box
END_ACTION = "logic.end"  # an End box: where the flow's box (in another flow) goes on; a named one is its own output
END_KEY = "_end"  # in a flow box's result: which End box was reached ("" = none)


@dataclass(frozen=True)
class Flow:
    """A saved graph of boxes, starting at Start; becomes the action flow.<name> (a button on Live, in SAMMI,
    over the API)."""

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

    @property
    def action_name(self) -> str:
        return f"flow.{self.name}"

    @property
    def outputs(self) -> tuple[str, ...]:
        """The names of its Flow output boxes (typed names only), in box order."""
        names = [str(n.params.get("name", "")).strip() for n in self.nodes if n.action == OUTPUT_ACTION]
        return tuple(dict.fromkeys(n for n in names if n and "${" not in n))

    @property
    def ends(self) -> tuple[str, ...]:
        """The names of its End boxes (typed names only), in box order: the outputs its box has in other flows.
        Empty: the box has one output (done), fired at an unnamed End box or when the flow is done."""
        names = [str(n.params.get("name", "")).strip() for n in self.nodes if n.action == END_ACTION]
        return tuple(dict.fromkeys(n for n in names if n and "${" not in n))

    @property
    def has_end(self) -> bool:
        return any(n.action == END_ACTION for n in self.nodes)

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
