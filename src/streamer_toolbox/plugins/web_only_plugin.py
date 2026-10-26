from pathlib import Path

from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin


class WebOnlyPlugin(ToolboxPlugin):
    """A plugin folder without code: plugin.json and a boxes/ folder of web boxes (WebBoxes) that talk to a web
    API. The loader makes one of these for it."""

    def __init__(self, boxes: Path) -> None:
        self._boxes = boxes

    def register(self, ctx: PluginContext) -> None:
        ctx.add_web_boxes(self._boxes)
