from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class ObsHotkey(ObsOutputBox):
    name = "trigger_hotkey"
    label = "OBS hotkey"
    help = "Does what one of OBS's hotkeys does (Settings → Hotkeys), without pressing a key"
    group = "Advanced"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"hotkey": self.hotkey_names}

    async def run(self, hotkey: str) -> None:
        await self._requests("TriggerHotkeyByName", {"hotkeyName": hotkey})
