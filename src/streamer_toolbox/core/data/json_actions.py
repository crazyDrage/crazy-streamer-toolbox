import json
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool


class JsonActions:
    """JSON boxes: text from a file or a web answer into a value (list / object) and back, e.g. to keep a list
    in a file with the Text file boxes (SAMMI's vts_saves.json)."""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("json.read", self.read, "Turns JSON text into a value (list, object, number, ...); save it in "
                    "a variable", "JSON text to value", group="JSON", flow_only=True)
        actions.add("json.write", self.write, "Turns a value into JSON text, e.g. to write it into a file",
                    "Value to JSON text", group="JSON", flow_only=True, typed=("value",))

    @staticmethod
    async def read(text: str) -> Any:
        try:
            return json.loads(text)
        except ValueError as e:
            raise ValueError(f"not JSON text: {e}") from None

    @staticmethod
    async def write(value: Any, pretty: bool = False) -> str:
        return json.dumps(value, indent=2 if to_bool(pretty) else None, ensure_ascii=False)
