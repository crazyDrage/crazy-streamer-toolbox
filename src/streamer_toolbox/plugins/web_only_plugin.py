from pathlib import Path

from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin


LEARN = "learn"  # next to boxes/: pages for the Learn tab


class WebOnlyPlugin(ToolboxPlugin):
    """A plugin folder without code: plugin.json and a boxes/ folder of web boxes (WebBoxes) that talk to a web
    API, maybe a learn/ folder of pages for the Learn tab. The loader makes one of these for it."""

    def __init__(self, boxes: Path) -> None:
        self._boxes = boxes

    def register(self, ctx: PluginContext) -> None:
        ctx.add_web_boxes(self._boxes)
        learn = self._boxes.parent / LEARN
        if learn.is_dir():
            ctx.add_learn_folder(learn)
