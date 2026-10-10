from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Request = Callable[..., Awaitable[dict[str, Any]]]  # (message type, data) → VTS's answer data


class VtsHotkeyActions:
    """VTube Studio's hotkeys of the loaded model: list them and fire one by name or id."""

    def __init__(self, request: Request) -> None:
        self._request = request

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("vts.trigger_hotkey", self.trigger_hotkey, "Fires a VTube Studio hotkey by name",
                    "Trigger hotkey", group="Hotkeys", options={"hotkey": self.hotkey_names})

    async def hotkey_names(self) -> list[str]:
        return [hotkey["name"] for hotkey in await self.hotkeys()]

    async def hotkeys(self) -> list[dict[str, Any]]:
        return (await self._request("HotkeysInCurrentModelRequest")).get("availableHotkeys", [])

    async def trigger_hotkey(self, hotkey: str) -> None:
        """hotkey = its name as shown in VTube Studio, or its ID."""
        await self._request("HotkeyTriggerRequest", {"hotkeyID": hotkey})
