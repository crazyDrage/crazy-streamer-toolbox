import json
from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class JsonTextToValue(Box):
    name = "read"
    label = "JSON text to value"
    help = "Turns JSON text into a value (list, object, number, ...); save it in a variable"
    group = "JSON"
    flow_only = True

    async def run(self, text: str) -> Any:
        try:
            return json.loads(text)
        except ValueError as e:
            raise ValueError(f"not JSON text: {e}") from None
