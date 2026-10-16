import re
from dataclasses import replace
from typing import Any

from streamer_toolbox.core.flows.flow_node import FlowNode

VALUE_ACTION = "logic.value"
OLD_LINE = "value"  # the name the one value of a box from before the lines gets


def lines_from_old_values(nodes: tuple[FlowNode, ...]) -> tuple[FlowNode, ...]:
    """A Value box from before the lines held one value ({"value": ...}, its result dot = ${box.n3}): it becomes
    one line named "value", and the wires from it move to that line (${box.n3} → ${box.n3.value}, also inside
    longer text and with a field after it)."""
    old = {n.id for n in nodes if n.action == VALUE_ACTION and "values" not in n.params and OLD_LINE in n.params}
    if not old:
        return nodes
    pattern = re.compile(r"\$\{box\.(" + "|".join(map(re.escape, old)) + r")(?=[.}])")
    moved = []
    for node in nodes:
        params = {k: _moved(v, pattern) for k, v in node.params.items()}
        if node.id in old:
            params = {k: v for k, v in params.items() if k != OLD_LINE} | {"values": {OLD_LINE: params[OLD_LINE]}}
        moved.append(replace(node, params=params) if params != node.params else node)
    return tuple(moved)


def _moved(value: Any, pattern: re.Pattern[str]) -> Any:
    if isinstance(value, str):
        return pattern.sub(lambda m: m.group(0) + "." + OLD_LINE, value)
    if isinstance(value, dict):
        return {k: _moved(v, pattern) for k, v in value.items()}
    return value
