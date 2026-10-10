from collections.abc import Callable

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_wire import START
from streamer_toolbox.core.flows.outline_entry import OutlineEntry


class FlowOutline:
    """A flow's graph as a list, the way SAMMI shows commands: a chain stays one flat list; boxes that run at
    the same time and the outputs of an If become indented blocks. ports_of(action, params) gives a box's outputs."""

    def __init__(self, flow: Flow, ports_of: Callable[[str, dict], tuple[str, ...]]) -> None:
        self._flow = flow
        self._ports_of = ports_of
        self._seen: set[str] = set()

    def build(self) -> tuple[OutlineEntry, ...]:
        self._seen = set()
        return self._after(START, "out")

    def loose(self) -> list[str]:
        """Boxes no wire from Start reaches (call after build)."""
        return [n.id for n in self._flow.nodes if n.id not in self._seen]

    def _after(self, source: str, port: str) -> tuple[OutlineEntry, ...]:
        targets = self._flow.targets(source, port)
        if len(targets) > 1:
            return (OutlineEntry("parallel", branches=tuple(("", self._from(t)) for t in targets)),)
        return self._from(targets[0]) if targets else ()

    def _from(self, node_id: str) -> tuple[OutlineEntry, ...]:
        node = self._flow.node(node_id)
        if node is None:
            return ()
        if node_id in self._seen:
            return (OutlineEntry("ref", node_id),)
        self._seen.add(node_id)
        ports = self._ports_of(node.action, node.params)
        if len(ports) == 1:
            return (OutlineEntry("node", node_id),) + self._after(node_id, ports[0])
        return (OutlineEntry("node", node_id, tuple((p, self._after(node_id, p)) for p in ports)),)
