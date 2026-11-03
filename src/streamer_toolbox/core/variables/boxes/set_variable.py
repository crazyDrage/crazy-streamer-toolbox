from typing import Any

from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class SetVariable(VariableBox):
    name = "set"
    label = "Set variable"
    help = "Stores a value in a variable (kept in a file)"
    group = "Variables"
    typed = ("value",)
    variable_fields = ("name",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, value: Any = "") -> Any:
        self.variables.set(name, value)
        return value
