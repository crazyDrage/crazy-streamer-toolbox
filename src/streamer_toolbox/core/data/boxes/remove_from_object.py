import copy
from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box


class RemoveFromObject(Box):
    name = "remove"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Remove from object"
    help = "The object without that key"
    group = "Change"
    flow_only = True

    async def run(self, object: Any, key: str) -> dict[str, Any]:
        whole = copy.deepcopy(_object(object))
        whole.pop(str(key), None)
        return whole
