import copy
from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import PAIRS, _object
from streamer_toolbox.core.interfaces.box import Box


class BuildObject(Box):
    name = "build"
    label = "Build object"
    help = "Builds an object from up to five name + value pairs (empty names are left out); 'start' = an object " \
           "to add them to"
    group = "Change"
    flow_only = True
    typed = tuple(f"value_{n}" for n in range(1, 6))

    async def run(self, start: Any = "", name_1: str = "", value_1: Any = "", name_2: str = "", value_2: Any = "",
                  name_3: str = "", value_3: Any = "", name_4: str = "", value_4: Any = "", name_5: str = "",
                  value_5: Any = "") -> dict[str, Any]:
        given = locals()
        whole = copy.deepcopy(_object(start))
        for i in range(1, PAIRS + 1):
            name = str(given[f"name_{i}"]).strip()
            if name:
                whole[name] = given[f"value_{i}"]
        return whole
