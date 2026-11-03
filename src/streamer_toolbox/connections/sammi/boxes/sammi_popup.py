from typing import Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox


class SammiPopup(SammiBox):
    name = "popup"
    label = "SAMMI popup"
    help = "Shows a popup message in SAMMI"
    group = "Messages"

    async def run(self, message: str) -> Any:
        return await self._sammi.send({"request": "popupMessage", "message": message})
