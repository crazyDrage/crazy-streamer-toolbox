import json
from typing import Any

from streamer_toolbox.connections.vnyan.vnyan_copy_texts import VNyanCopyTexts
from streamer_toolbox.core.interfaces.box import Box


class VNyanDataBlock(Box):
    """Send data to VNyan's "Copy VNyan block" (his 11-22: "it will use the json and template and we get all
    values"): a WebSocket Command node with an empty Command Text and a Dictionary Values node with one key per
    value, to paste into VNyan. Not in the Add box window."""

    name = "data_block"
    label = "VNyan block for data"
    help = "The VNyan nodes that read these values, as a text to paste into a VNyan node graph"
    offered = False

    def __init__(self, texts: VNyanCopyTexts) -> None:
        self._texts = texts

    async def run(self, data: Any) -> str:
        return self._texts.data_block(_keys(data))


def _keys(data: Any) -> list[str]:
    """The names of the values: an object's keys (typed, or known from the wire), or names with commas between."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return [name.strip() for name in data.split(",")]
    if isinstance(data, dict):
        return [str(name) for name in data]
    raise ValueError('Which values? An object like {"command": "throw"}')
