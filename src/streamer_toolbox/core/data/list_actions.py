import random
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import same, to_bool, to_list
from streamer_toolbox.core.variables.variable_store import VariableStore

PLACES = ["end", "start"]


class ListActions:
    """List boxes (SAMMI's arrays), e.g. the names of the saved VTS spots. Add / Remove change a list variable;
    the others take a list (by wire or ${var.name}) and give back a value or a new list (store it with Set
    variable to keep it). Positions count from 1; -1 is the last one."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    def add_to(self, actions: ActionRegistry) -> None:
        async def names() -> list[str]:
            return self._variables.names()

        async def places() -> list[str]:
            return PLACES

        actions.add("list.add", self.add, "Adds a value to a list variable, at the end or the start; a variable that "
                    "doesn't exist yet starts empty. Only once: skip it if it's already in", "Add to list",
                    group="Change", options={"name": names, "where": places}, typed=("value",))
        actions.add("list.remove", self.remove, "Takes every copy of a value out of a list variable",
                    "Remove from list", group="Change", options={"name": names})
        actions.add("list.contains", self.contains, "Goes on through 'then' if the list has the value, else "
                    "through 'else'", "List has", group="Read", ports=("then", "else"), flow_only=True)
        actions.add("list.size", self.size, "How many values the list has", "List size", group="Read",
                    flow_only=True)
        actions.add("list.get", self.get, "The value at a position: 1 = first, -1 = last", "Get from list",
                    group="Read", flow_only=True, typed=("default",))
        actions.add("list.random", self.pick_random, "A random value from the list", "Random from list",
                    group="Read", flow_only=True)
        actions.add("list.find", self.find, "Where the value is in the list (1 = first), 0 if it isn't there",
                    "Find in list", group="Read", flow_only=True)
        actions.add("list.insert", self.insert, "The list with a value put in at a position (1 = first, empty = "
                    "at the end)", "Insert into list", group="New list", flow_only=True, typed=("value",))
        actions.add("list.remove_at", self.remove_at, "The list without the value at a position (1 = first, -1 = "
                    "last)", "Remove at position", group="New list", flow_only=True)
        actions.add("list.sort", self.sort, "The list sorted (numbers by value, text A-Z); by = a field to sort "
                    "objects by, e.g. value for Top viewers", "Sort list", group="New list", flow_only=True)
        actions.add("list.shuffle", self.shuffle, "The list in a random order", "Shuffle list", group="New list",
                    flow_only=True)

    async def add(self, name: str, value: Any, where: str = "end", only_once: bool = False) -> list[Any]:
        if where not in PLACES:
            raise ValueError(f"where must be one of {', '.join(PLACES)}, not {where!r}")
        items = to_list(self._variables.get(name))
        if not (to_bool(only_once) and any(same(i, value) for i in items)):
            items.insert(0 if where == "start" else len(items), value)
        self._variables.set(name, items)
        return items

    async def remove(self, name: str, value: Any) -> list[Any]:
        items = [i for i in to_list(self._variables.get(name)) if not same(i, value)]
        self._variables.set(name, items)
        return items

    @staticmethod
    async def contains(items: Any, value: Any) -> bool:
        return any(same(i, value) for i in to_list(items))

    @staticmethod
    async def size(items: Any) -> int:
        return len(to_list(items))

    @staticmethod
    async def get(items: Any, position: int = 1, default: Any = "") -> Any:
        """default: given back when there's no such position (empty = the box fails)."""
        values, position = to_list(items), int(position)
        if position == 0 or abs(position) > len(values):
            if default not in ("", None):
                return default
            raise IndexError(f"no position {position} in a list of {len(values)}")
        return values[position - 1 if position > 0 else position]

    @staticmethod
    async def find(items: Any, value: Any) -> int:
        return next((i for i, item in enumerate(to_list(items), 1) if same(item, value)), 0)

    @staticmethod
    async def insert(items: Any, value: Any, position: int | None = None) -> list[Any]:
        values = to_list(items)
        if position in (None, ""):
            return values + [value]
        position = int(position)
        values.insert(position - 1 if position > 0 else len(values) + position + 1, value)
        return values

    @staticmethod
    async def remove_at(items: Any, position: int = -1) -> list[Any]:
        values, position = to_list(items), int(position)
        if position == 0 or abs(position) > len(values):
            raise IndexError(f"no position {position} in a list of {len(values)}")
        del values[position - 1 if position > 0 else position]
        return values

    @staticmethod
    async def sort(items: Any, descending: bool = False, by: str = "") -> list[Any]:
        def key(item: Any) -> tuple:
            value = item.get(by, "") if by and isinstance(item, dict) else item
            try:
                return 0, float(value), ""
            except (TypeError, ValueError):
                return 1, 0.0, str(value).casefold()

        return sorted(to_list(items), key=key, reverse=to_bool(descending))

    @staticmethod
    async def shuffle(items: Any) -> list[Any]:
        values = to_list(items)
        random.shuffle(values)
        return values

    @staticmethod
    async def pick_random(items: Any) -> Any:
        values = to_list(items)
        if not values:
            raise IndexError("the list is empty")
        return random.choice(values)
