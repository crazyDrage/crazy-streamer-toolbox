from typing import Any

from streamer_toolbox.core.variables.boxes.viewer_box import ViewerBox, _key
from streamer_toolbox.core.variables.variable_store import VariableStore


class GetViewerValue(ViewerBox):
    name = "get"
    label = "Get viewer value"
    help = "A viewer's value in a per-viewer variable (default if they have none yet)"
    group = "Per viewer"
    flow_only = True
    data_only = True  # the toolbox's own value: no run wire, read when a box needs it (his round 62 A)
    typed = ("default",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, user: str, default: Any = "") -> Any:
        return self._all(name).get(_key(user), default)
