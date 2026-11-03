from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class End(Box):
    name = "end"
    label = "End"
    help = "The end of this flow when another flow uses it as a box: there that box goes on as soon as the End box " \
           "is reached, and gets its values, each as an orange dot named like its line (+ Add value). A flow has " \
           "one End box"
    group = "Flow"
    flow_only = True
    named_lines = True
    ends_flow = True
    once_per_flow = True

    async def run(self, **values: Any) -> dict[str, Any]:
        """Its values, by name (the FlowRunner hands them to the flow's box)."""
        return values
