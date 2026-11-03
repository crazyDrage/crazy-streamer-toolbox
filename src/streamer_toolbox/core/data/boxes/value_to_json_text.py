import json
from typing import Any

from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box


class ValueToJsonText(Box):
    name = "write"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Value to JSON text"
    help = "Turns a value into JSON text, e.g. to write it into a file"
    group = "JSON"
    flow_only = True
    typed = ("value",)

    async def run(self, value: Any, pretty: bool = False) -> str:
        return json.dumps(value, indent=2 if to_bool(pretty) else None, ensure_ascii=False)
