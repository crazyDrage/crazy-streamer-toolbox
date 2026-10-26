from streamer_toolbox.connections.vtube_studio.boxes.vts_hotkey_box import VtsHotkeyBox, Request


class TriggerHotkey(VtsHotkeyBox):
    name = "trigger_hotkey"
    label = "Trigger hotkey"
    help = "Fires a VTube Studio hotkey by name"
    group = "Hotkeys"

    def __init__(self, request: Request) -> None:
        super().__init__(request)
        self.options = {"hotkey": self.hotkey_names}

    async def run(self, hotkey: str) -> None:
        """hotkey = its name as shown in VTube Studio, or its ID."""
        await self._request("HotkeyTriggerRequest", {"hotkeyID": hotkey})
