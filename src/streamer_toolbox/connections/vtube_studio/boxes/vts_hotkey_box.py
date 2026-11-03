from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Request = Callable[..., Awaitable[dict[str, Any]]]


class VtsHotkeyBox(Box):
    """What the vts hotkey boxes share (not a box itself: it has no run).

    VTube Studio's hotkeys of the loaded model: list them and fire one by name or id."""

    def __init__(self, request: Request) -> None:
        self._request = request

    async def hotkey_names(self) -> list[str]:
        return [hotkey["name"] for hotkey in await self.hotkeys()]

    async def hotkeys(self) -> list[dict[str, Any]]:
        return (await self._request("HotkeysInCurrentModelRequest")).get("availableHotkeys", [])
