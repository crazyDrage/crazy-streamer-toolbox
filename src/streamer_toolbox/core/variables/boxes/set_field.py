import copy
from typing import Any

from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class SetField(VariableBox):
    name = "set_field"
    label = "Set field"
    help = "Sets one field of an object variable (a.b for a field inside a field); a variable that doesn't exist " \
           "yet starts as an empty object"
    group = "Variables"
    typed = ("value",)
    variable_fields = ("name",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, field: str, value: Any = "") -> dict[str, Any]:
        whole = understand(self.variables.get(name, {}))  # also an object typed into Set variable as JSON text
        if not isinstance(whole, dict):
            raise ValueError(f"variable {name} is not an object ({whole!r})")
        whole = copy.deepcopy(whole)
        *path, last = str(field).split(".")
        inner = whole
        for part in path:
            if not isinstance(inner.get(part, {}), dict):
                raise ValueError(f"{name}.{part} is not an object")
            inner = inner.setdefault(part, {})
        inner[last] = value
        self.variables.set(name, whole)
        return whole
