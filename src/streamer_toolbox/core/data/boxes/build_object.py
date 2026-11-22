import copy
from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class BuildObject(Box):
    """An object from lines he names (his 11-22: "it should look more like the Input box, and adding variables";
    "remove the start input, because we have a combine object box": Join objects does that). Each line is a key
    with a dot to wire into or a value typed in (named_lines, like Build text and End). Before settings version 8
    it had five name + value pairs and a start object (BuildObjectUpgrade)."""

    name = "build"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Build object"
    help = "Builds an object: + Add value for each key, then wire into its dot or type its value. To add to an " \
           "object you have: Join objects"
    group = "Change"
    flow_only = True
    named_lines = True

    async def run(self, **values: Any) -> dict[str, Any]:
        return copy.deepcopy(values)
