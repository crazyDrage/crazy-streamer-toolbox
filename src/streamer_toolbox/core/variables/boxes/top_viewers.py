from typing import Any

from streamer_toolbox.core.variables.boxes.viewer_box import ViewerBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class TopViewers(ViewerBox):
    name = "top"
    label = "Top viewers"
    help = "The viewers with the highest numbers, as a list of {user, value}"
    group = "Per viewer"
    flow_only = True

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, count: int = 5) -> list[dict[str, Any]]:
        numbers = []
        for user, value in self._all(name).items():
            try:
                numbers.append({"user": user, "value": float(value) if not isinstance(value, int) else value})
            except (TypeError, ValueError):
                continue
        return sorted(numbers, key=lambda n: n["value"], reverse=True)[:max(int(count), 0)]
