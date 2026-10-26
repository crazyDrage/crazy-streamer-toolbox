from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Show = Callable[[str, str, bool, Any], None]  # source, what, ok, text: the Recent list's add


class Debug(Box):
    """Takes a value, shows it and gives it on unchanged. For trying other boxes: wire a result into it to see
    what really came out, or type a value into it to feed the next box.

    `show` gets what it shows (the Recent list on the Live page); the flow editor shows the value on the box
    as well, like any box's last result."""

    name = "debug"
    label = "Debug"
    help = "Shows a value and gives it on unchanged: wire a box's result into it to see what really came out (in " \
           "Recent on the Live page, and on this box after a run), or type a value to feed the next box. Text " \
           "shows in quotes, a number or true/false without"
    group = "Flow"
    flow_only = True
    typed = ("value",)
    hints = {"name": "What to call it in Recent, e.g. 'after the split'. Empty = Debug",
             "value": "Wire a result dot into it, or type a value"}

    def __init__(self, show: Show | None = None) -> None:
        self._show = show

    async def run(self, value: Any = "", name: str = "") -> Any:
        if self._show:
            self._show("Debug", str(name).strip() or "Debug", True, f"{value!r} ({type(value).__name__})")
        return value
