from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _key, _object
from streamer_toolbox.core.flows.box_wire import field_of
from streamer_toolbox.core.interfaces.box import Box


class GetFromObject(Box):
    name = "get"
    label = "Get from object"
    help = "One value of an object by its key (the key can come by wire, e.g. a name from a list). If it isn't " \
           "there: the default, or the box fails when that's empty"
    group = "Read"
    flow_only = True
    data_only = True  # no run wire: it runs whenever a box needs its value (his OPEN 92)
    typed = ("default",)

    async def run(self, object: Any, key: str, default: Any = "") -> Any:
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
