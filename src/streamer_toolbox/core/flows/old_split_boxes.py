import re
from dataclasses import replace
from typing import Any

from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_wire import FlowWire

SPLIT_ACTION = "data.split"
SOURCE = re.compile(r"\$\{(\w+\.[\w.@]+)\}")  # what a Split box took apart: ${box.n1}, ${var.pos}, ...


def split_boxes_away(nodes: tuple[FlowNode, ...],
                     wires: tuple[FlowWire, ...]) -> tuple[tuple[FlowNode, ...], tuple[FlowWire, ...]]:
    """Split data is gone (his round 51: a box's fields are dots of their own). A Split box's fields are wired
    from what it took apart instead: ${box.n2.width} → ${box.n1.width} when n2 split ${box.n1}. The box goes,
    and a run wire through it is bridged. A Split box whose data isn't one ${...} stays (an unknown box)."""
    sources = {n.id: match.group(1) for n in nodes if n.action == SPLIT_ACTION
               and (match := SOURCE.fullmatch(str(n.params.get("data", ""))))}
    if not sources:
        return nodes, wires
    pattern = re.compile(r"\$\{box\.(" + "|".join(map(re.escape, sources)) + r")((?:\.[\w@]+)*)\}")
    for _ in sources:  # a Split box after a Split box: to what the first one took apart
        sources = {k: _moved("${" + v + "}", pattern, sources)[2:-1] for k, v in sources.items()}
    kept = tuple(replace(n, params={k: _moved(v, pattern, sources) for k, v in n.params.items()})
                 for n in nodes if n.id not in sources)
    bridged = [w for w in wires if w.source not in sources and w.target not in sources]
    for split in sources:
        bridged += [FlowWire(i.source, i.port, o.target, o.entry) for i in wires if i.target == split
                    for o in wires if o.source == split]
    return kept, tuple(dict.fromkeys(bridged))


def _moved(value: Any, pattern: re.Pattern[str], sources: dict[str, str]) -> Any:
    if isinstance(value, str):
        return pattern.sub(lambda m: "${" + sources[m.group(1)] + m.group(2) + "}", value)
    if isinstance(value, dict):
        return {k: _moved(v, pattern, sources) for k, v in value.items()}
    return value
