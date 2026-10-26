from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.variables.variable_store import VariableStore


class VariableBox(Box):
    """What the boxes that work on a variable share: the variables, and `names` for the picker of the field that
    holds a variable's name (set as `options` by each box). Not a box itself: it has no run."""

    def __init__(self, variables: VariableStore) -> None:
        self.variables = variables

    async def names(self) -> list[str]:
        return self.variables.names()
