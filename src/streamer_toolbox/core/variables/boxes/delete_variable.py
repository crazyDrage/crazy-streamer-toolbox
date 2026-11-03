from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class DeleteVariable(VariableBox):
    name = "delete"
    label = "Delete variable"
    help = "Removes a variable (and its file). A variable that doesn't exist is fine: nothing happens. Gives " \
           "whether there was one"
    group = "Variables"
    variable_fields = ("name",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str) -> bool:
        there = name in self.variables.names()
        self.variables.delete(name)
        return there
