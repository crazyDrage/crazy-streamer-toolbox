from dataclasses import replace

from streamer_toolbox.core.flows.flow import END_ACTION, Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import START, FlowWire

TRIGGER_ID = "t"  # a trigger's Start box: t1, t2, ...
END_ID = "end"
END_SPOT = (420.0, 20.0)


def free_trigger_id(taken: list[str] | tuple[str, ...]) -> str:
    numbers = [int(i[1:]) for i in taken if i[:1] == TRIGGER_ID and i[1:].isdigit()]
    return f"{TRIGGER_ID}{max(numbers, default=0) + 1}"


def first_wires(trigger_id: str, wires: list[FlowWire] | tuple[FlowWire, ...]) -> list[FlowWire]:
    """The run wires a new trigger's Start box gets (his round 63): the same as the Manual Start's, so it starts
    what Start starts (in a new flow: the End box)."""
    return [FlowWire(trigger_id, "out", w.target, w.entry) for w in wires if w.source == START]


def with_trigger(flow: Flow, trigger: FlowTrigger) -> Flow:
    """The flow with one more trigger, as its own Start box wired like the Manual Start."""
    trigger_id = free_trigger_id([t.id for t in flow.triggers])
    return replace(flow, triggers=(*flow.triggers, replace(trigger, id=trigger_id)),
                   wires=(*flow.wires, *first_wires(trigger_id, flow.wires)))


def new_flow(name: str, label: str, **more) -> Flow:
    """A new flow (his round 63): Start wired to an End box, the boxes go in between."""
    flow = Flow(name, label, nodes=(FlowNode(END_ID, END_ACTION, box=END_SPOT),),
                wires=(FlowWire(START, "out", END_ID),), **{k: v for k, v in more.items() if k != "triggers"})
    for trigger in more.get("triggers", ()):
        flow = with_trigger(flow, trigger)
    return flow
