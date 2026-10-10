import copy
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_kind
from streamer_toolbox.core.flows.box_wire import field_of

PAIRS = 5  # Build object: name_1 / value_1 ... name_5 / value_5


class ObjectActions:
    """Object boxes (SAMMI's Object commands): read, change and build objects that come by wire or from a
    variable (${var.name}). Changing gives back a new object; store it with Set variable to keep it. Reading
    finds a key in any upper / lower case if there's no exact one.
    A key may be a path: "right_arm.id" is the id inside right_arm, "outputs.0" the first of a list."""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("object.get", self.get, "One value of an object by its key (the key can come by wire, e.g. "
                    "a name from a list). If it isn't there: the default, or the box fails when that's empty",
                    "Get from object", group="Read", flow_only=True, typed=("default",))
        actions.add("object.has", self.has, "Goes on through 'then' if the object has the key, else 'else'",
                    "Object has key", group="Read", ports=("then", "else"), flow_only=True)
        actions.add("object.keys", self.keys, "Every key of the object, as a list (e.g. for For each)",
                    "Object keys", group="Read", flow_only=True)
        actions.add("object.values", self.values, "Every value of the object, as a list", "Object values",
                    group="Read", flow_only=True)
        actions.add("object.set", self.set, "The object with one key set to a value (added or replaced). Gives "
                    "back the new object; empty object = start a new one", "Set in object", group="Change",
                    flow_only=True, typed=("value",))
        actions.add("object.remove", self.remove, "The object without that key", "Remove from object",
                    group="Change", flow_only=True)
        actions.add("object.build", self.build, "Builds an object from up to five name + value pairs (empty names "
                    "are left out); 'start' = an object to add them to", "Build object", group="Change",
                    flow_only=True, typed=tuple(f"value_{n}" for n in range(1, 6)))

    @staticmethod
    async def get(object: Any, key: str, default: Any = "") -> Any:
        whole, key = _object(object), _key(object, key)
        if key in whole:
            return whole[key]
        try:
            return field_of(whole, key, "the object")
        except KeyError:
            if default in ("", None):
                keys = ", ".join(map(str, whole)) or "none"
                raise KeyError(f"the object has no key {key!r} (it has: {keys})") from None
            return default

    @staticmethod
    async def has(object: Any, key: str) -> bool:
        whole, key = _object(object), _key(object, key)
        if key in whole:
            return True
        try:
            field_of(whole, key, "the object")
        except KeyError:
            return False
        return True

    @staticmethod
    async def keys(object: Any) -> list[str]:
        return list(_object(object))

    @staticmethod
    async def values(object: Any) -> list[Any]:
        return list(_object(object).values())

    @staticmethod
    async def set(object: Any, key: str, value: Any = "") -> dict[str, Any]:
        whole, key = copy.deepcopy(_object(object)), str(key)
        *path, last = [key] if key in whole else key.split(".")
        inner = whole
        for part in path:
            if not isinstance(inner.setdefault(part, {}), dict):
                raise ValueError(f"{part!r} in the object is not an object")
            inner = inner[part]
        inner[last] = value
        return whole

    @staticmethod
    async def remove(object: Any, key: str) -> dict[str, Any]:
        whole = copy.deepcopy(_object(object))
        whole.pop(str(key), None)
        return whole

    @staticmethod
    async def build(start: Any = "", name_1: str = "", value_1: Any = "", name_2: str = "", value_2: Any = "",
                    name_3: str = "", value_3: Any = "", name_4: str = "", value_4: Any = "", name_5: str = "",
                    value_5: Any = "") -> dict[str, Any]:
        given = locals()
        whole = copy.deepcopy(_object(start))
        for i in range(1, PAIRS + 1):
            name = str(given[f"name_{i}"]).strip()
            if name:
                whole[name] = given[f"value_{i}"]
        return whole


def _object(value: Any) -> dict[str, Any]:
    """An empty field is an empty object; JSON text of an object is read."""
    if value is None or value == "":
        return {}
    return to_kind(value, "object")


def _key(value: Any, key: Any) -> str:
    """The key as the object has it: "LL" finds "ll" when there's no "LL" (viewers type in any case)."""
    key, whole = str(key), _object(value)
    if key in whole:
        return key
    return next((k for k in whole if str(k).casefold() == key.casefold()), key)
