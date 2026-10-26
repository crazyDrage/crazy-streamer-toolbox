from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box


class ObjectValues(Box):
    name = "values"
    label = "Object values"
    help = "Takes an object apart: one orange dot per key (x, y, ...), following what is wired in. result = the " \
           "whole object; its @values = every value as a list"
    group = "Read"
    flow_only = True
    keys_of = "object"

    async def run(self, object: Any) -> dict[str, Any]:
        """The object itself: each key's dot reads its own value from it (his round 60, like Get model position)."""
        return dict(_object(object))
