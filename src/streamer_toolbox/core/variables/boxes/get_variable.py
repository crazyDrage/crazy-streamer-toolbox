from typing import Any

from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class GetVariable(VariableBox):
    name = "get"
    label = "Get variable"
    help = "Gives a variable's value as it is right now: wire its orange dot into other boxes' fields. It needs no " \
           "run wire, it reads the variable each time a box needs it"
    group = "Variables"
    data_only = True
    variable_fields = ("name",)
    hints = {"field": "Optional: one field of an object variable, e.g. x of a position (a.b for a field inside a "
                      "field)"}

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, field: str = "") -> Any:
        return self.variables.lookup(f"{name}.{field}" if field else name)
