import copy
from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box


class RemoveFromObject(Box):
    name = "remove"
    label = "Remove from object"
    help = "The object without that key"
    group = "Change"
    flow_only = True

    async def run(self, object: Any, key: str) -> dict[str, Any]:
        whole = copy.deepcopy(_object(object))
        whole.pop(str(key), None)
        return whole
