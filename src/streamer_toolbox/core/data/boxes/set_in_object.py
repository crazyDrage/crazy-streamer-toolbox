import copy
from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box


class SetInObject(Box):
    name = "set"
    label = "Set in object"
    help = "The object with one key set to a value (added or replaced). Gives back the new object; empty object " \
           "= start a new one"
    group = "Change"
    flow_only = True
    typed = ("value",)

    async def run(self, object: Any, key: str, value: Any = "") -> dict[str, Any]:
        whole, key = copy.deepcopy(_object(object)), str(key)
        *path, last = [key] if key in whole else key.split(".")
        inner = whole
        for part in path:
            if not isinstance(inner.setdefault(part, {}), dict):
                raise ValueError(f"{part!r} in the object is not an object")
            inner = inner[part]
        inner[last] = value
        return whole
