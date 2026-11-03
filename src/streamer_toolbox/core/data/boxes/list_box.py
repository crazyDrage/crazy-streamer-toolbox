from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.variables.variable_store import VariableStore


PLACES = ["end", "start"]


class ListBox(Box):
    """What the list boxes share (not a box itself: it has no run).

    List boxes (SAMMI's arrays), e.g. the names of the saved VTS spots. Add / Remove change a list variable;
    the others take a list (by wire or ${var.name}) and give back a value or a new list (store it with Set
    variable to keep it). Positions count from 1; -1 is the last one."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    async def names(self) -> list[str]:
        return self._variables.names()
