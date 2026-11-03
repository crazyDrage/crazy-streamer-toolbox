from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class FlowOutput(Box):
    name = "output"
    label = "Flow output"
    help = "What this flow gives back when another flow uses it as a box: each Flow output box becomes an orange " \
           "dot on that box, named like this box"
    group = "Flow"
    flow_only = True
    typed = ("value",)
    gives_back = "name"

    async def run(self, name: str, value: Any = "") -> Any:
        """The FlowRunner collects it under `name`."""
        return value
