import re
from dataclasses import replace

from streamer_toolbox.core.flows.flow import END_ACTION, END_LINE
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_wire import FlowWire

OLD_LINE = re.compile(rf"{END_LINE}_(\d+)")  # an End box's lines of round 53: name_1, name_2, ... (a run dot each)
OLD_COUNT = END_LINE + "s"  # how many lines it had


def end_boxes_from_lines(nodes: tuple[FlowNode, ...],
                         wires: tuple[FlowWire, ...]) -> tuple[tuple[FlowNode, ...], tuple[FlowWire, ...]]:
    """An End box had names until round 55: one per box (its way out, `name`), in round 53 a run dot per name
    (name_1, name_2, ...). Since round 55 a flow has one End box with one run dot and one output on the flow's
    box; its params are only the values it gives back. The names go, and the wires into a name's run dot go into
    the box's run dot."""
    ends = {n.id for n in nodes if n.action == END_ACTION}
    old = {n.id for n in nodes if n.id in ends and any(_named(k) for k in n.params)}
    if not old and not any(w.target in ends and w.entry for w in wires):
        return nodes, wires
    new_nodes = tuple(replace(n, params={k: v for k, v in n.params.items() if not _named(k)}) if n.id in old else n
                      for n in nodes)
    new_wires = tuple(dict.fromkeys(replace(w, entry="") if w.target in ends and w.entry else w for w in wires))
    return new_nodes, new_wires


def _named(key: str) -> bool:
    return key in (END_LINE, OLD_COUNT) or bool(OLD_LINE.fullmatch(key))
