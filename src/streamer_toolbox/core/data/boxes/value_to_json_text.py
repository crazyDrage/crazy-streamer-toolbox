import json
from typing import Any

from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box


class ValueToJsonText(Box):
    name = "write"
    label = "Value to JSON text"
    help = "Turns a value into JSON text, e.g. to write it into a file"
    group = "JSON"
    flow_only = True
    typed = ("value",)

    async def run(self, value: Any, pretty: bool = False) -> str:
        return json.dumps(value, indent=2 if to_bool(pretty) else None, ensure_ascii=False)
