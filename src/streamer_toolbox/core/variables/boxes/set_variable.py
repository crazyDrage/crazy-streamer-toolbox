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
    labels = {"only_if_new": "Create if none"}
    hints = {"only_if_new": "On: only when there is no such variable yet (it gets this value); one that exists "
                            "keeps its own, and that is what goes on. So Get variable always finds it (his round "
                            "90)"}

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, value: Any = "", only_if_new: bool = False) -> Any:
        if only_if_new and name in self.variables.names():
            return self.variables.get(name)
        self.variables.set(name, value)
        return value
