from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _key, _object
from streamer_toolbox.core.flows.box_wire import field_of
from streamer_toolbox.core.interfaces.box import Box


class ObjectHasKey(Box):
    name = "has"
    label = "Object has key"
    help = "Goes on through 'then' if the object has the key, else 'else'"
    group = "Read"
    ports = ("then", "else")
    flow_only = True

    async def run(self, object: Any, key: str) -> bool:
        whole, key = _object(object), _key(object, key)
        if key in whole:
            return True
        try:
            field_of(whole, key, "the object")
        except KeyError:
            return False
        return True
