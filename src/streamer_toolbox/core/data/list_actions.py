from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.boxes.add_to_list import AddToList
from streamer_toolbox.core.data.boxes.find_in_list import FindInList
from streamer_toolbox.core.data.boxes.get_from_list import GetFromList
from streamer_toolbox.core.data.boxes.insert_into_list import InsertIntoList
from streamer_toolbox.core.data.boxes.list_has import ListHas
from streamer_toolbox.core.data.boxes.list_size import ListSize
from streamer_toolbox.core.data.boxes.random_from_list import RandomFromList
from streamer_toolbox.core.data.boxes.remove_at_position import RemoveAtPosition
from streamer_toolbox.core.data.boxes.remove_from_list import RemoveFromList
from streamer_toolbox.core.data.boxes.shuffle_list import ShuffleList
from streamer_toolbox.core.data.boxes.sort_list import SortList
from streamer_toolbox.core.variables.variable_store import VariableStore


class ListActions:
    """List boxes (SAMMI's arrays), e.g. the names of the saved VTS spots. Add / Remove change a list variable;
    the others take a list (by wire or ${var.name}) and give back a value or a new list (store it with Set
    variable to keep it). Positions count from 1; -1 is the last one.

    One Box class per box, in boxes/."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (AddToList(self._variables), RemoveFromList(self._variables), ListHas(), ListSize(),
                    GetFromList(), RandomFromList(), FindInList(), InsertIntoList(), RemoveAtPosition(), SortList(),
                    ShuffleList()):
            actions.add_box(box, "list")
