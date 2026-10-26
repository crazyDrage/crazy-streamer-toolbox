from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class Value(Box):
    name = "value"
    label = "Value"
    help = "Values you type once (e.g. your model's name, a power of 10) and wire into as many boxes as you like: " \
           "every line is an orange dot of its own. Change it here, every box gets it. Numbers, true/false and JSON " \
           "stay what they are"
    group = "Flow"
    flow_only = True
    value_lines = "values"
    typed = ("value",)
    data_only = True
    hints = {"values": "Wire a line's orange dot into the fields that need it; it has no run wire"}

    async def run(self, values: dict[str, Any] | None = None, **old: Any) -> Any:
        """Its lines, by name (typed by hand they arrive read already, see FlowRunner). `old` is the one value of a
        box from before the lines, {"value": ...}: a flow file turns it into a line when it is read
        (old_value_boxes), but an API call may still send it."""
        return dict(values) if values else old.get("value", "")
