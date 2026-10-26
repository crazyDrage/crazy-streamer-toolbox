from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.box_value import same, to_bool, to_list
from streamer_toolbox.core.data.boxes.list_box import ListBox, PLACES
from streamer_toolbox.core.variables.variable_store import VariableStore


class AddToList(ListBox):
    name = "add"
    label = "Add to list"
    help = "Adds a value to a list variable, at the end or the start; a variable that doesn't exist yet starts " \
           "empty. Only once: skip it if it's already in"
    group = "Change"
    typed = ("value",)
    variable_fields = ("name",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names, "where": fixed_choices(PLACES)}

    async def run(self, name: str, value: Any, where: str = "end", only_once: bool = False) -> list[Any]:
        if where not in PLACES:
            raise ValueError(f"where must be one of {', '.join(PLACES)}, not {where!r}")
        items = to_list(self._variables.get(name))
        if not (to_bool(only_once) and any(same(i, value) for i in items)):
            items.insert(0 if where == "start" else len(items), value)
        self._variables.set(name, items)
        return items
