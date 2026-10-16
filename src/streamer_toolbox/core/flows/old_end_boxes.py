from dataclasses import replace

from streamer_toolbox.core.flows.flow import END_ACTION, END_LINE
from streamer_toolbox.core.flows.flow_node import FlowNode


def end_lines_from_old_names(nodes: tuple[FlowNode, ...]) -> tuple[FlowNode, ...]:
    """An End box from before its lines held one name ({"name": ...}): it becomes line 1 (name_1). The wires into
    its run dot stay as they are: a wire into an End box's normal run dot counts as line 1."""
    first = f"{END_LINE}_1"
    return tuple(replace(n, params={(first if k == END_LINE else k): v for k, v in n.params.items()})
                 if n.action == END_ACTION and END_LINE in n.params and first not in n.params else n
                 for n in nodes)
