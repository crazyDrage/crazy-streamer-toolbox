from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box


class ObjectKeys(Box):
    name = "keys"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Object keys"
    help = "Every key of the object, as a list (e.g. for For each)"
    group = "Read"
    flow_only = True

    async def run(self, object: Any) -> list[str]:
        return list(_object(object))
