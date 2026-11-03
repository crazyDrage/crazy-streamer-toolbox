from typing import Any

from streamer_toolbox.core.variables.boxes.viewer_box import ViewerBox, _key
from streamer_toolbox.core.variables.variable_store import VariableStore


class SetViewerValue(ViewerBox):
    name = "set"
    label = "Set viewer value"
    help = "Sets a viewer's value in a per-viewer variable"
    group = "Per viewer"
    flow_only = True
    typed = ("value",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, user: str, value: Any = "") -> Any:
        values = self._all(name)
        values[_key(user)] = value
        self._variables.set(name, values)
        return value
