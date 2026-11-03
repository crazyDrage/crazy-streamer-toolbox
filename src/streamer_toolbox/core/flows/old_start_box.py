import re
from dataclasses import replace
from typing import Any

from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import INPUT, FlowWire
from streamer_toolbox.core.flows.start_boxes import first_wires, free_trigger_id

START_REF = re.compile(r"\$\{box\.start\.(\w+)")  # ${box.start.user...}: one field of the old Start box


def start_boxes_from_triggers(nodes: tuple[FlowNode, ...], wires: tuple[FlowWire, ...],
                              triggers: tuple[FlowTrigger, ...], inputs: tuple[FlowInput, ...]
                              ) -> tuple[tuple[FlowNode, ...], tuple[FlowWire, ...], tuple[FlowTrigger, ...]]:
    """Until round 63 a flow had one Start box for everything: its button, its triggers and its inputs as orange
    dots. Now each trigger is a Start box of its own and the inputs are on the Input box. A trigger without an id
    (an older file) gets one and the Manual Start's run wires; a field wired to the old Start box reads the Input
    box for an input, else the first trigger that gives that field (else the first trigger)."""
    taken = [t.id for t in triggers if t.id]
    new = []
    for trigger in triggers:
        if trigger.id:
            new.append(trigger)
            continue
        trigger = replace(trigger, id=free_trigger_id(taken))
        taken.append(trigger.id)
        wires = (*wires, *first_wires(trigger.id, wires))
        new.append(trigger)
    names = {i.name for i in inputs}

    def moved(match: re.Match) -> str:
        field = match.group(1)
        if field in names:
            return f"${{box.{INPUT}.{field}"
        giving = next((t for t in new if field in EVENT_FIELDS.get(t.kind, ())), new[0] if new else None)
        return f"${{box.{giving.id}.{field}" if giving else match.group(0)

    nodes = tuple(replace(n, params=_rewrite(n.params, moved)) if _has_ref(n.params) else n for n in nodes)
    return nodes, tuple(dict.fromkeys(wires)), tuple(new)


def _has_ref(value: Any) -> bool:
    if isinstance(value, str):
        return START_REF.search(value) is not None
    if isinstance(value, dict):
        return any(_has_ref(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_ref(v) for v in value)
    return False


def _rewrite(value: Any, moved) -> Any:
    if isinstance(value, str):
        return START_REF.sub(moved, value)
    if isinstance(value, dict):
        return {k: _rewrite(v, moved) for k, v in value.items()}
    if isinstance(value, list):
        return [_rewrite(v, moved) for v in value]
    return value
