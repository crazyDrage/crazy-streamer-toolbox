from typing import Any

from streamer_toolbox.core.data.box_value import same, to_list
from streamer_toolbox.core.data.boxes.list_box import ListBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class RemoveFromList(ListBox):
    name = "remove"
    label = "Remove from list"
    help = "Takes every copy of a value out of a list variable"
    group = "Change"
    variable_fields = ("name",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, value: Any) -> list[Any]:
        items = [i for i in to_list(self._variables.get(name)) if not same(i, value)]
        self._variables.set(name, items)
        return items
