from typing import Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox


class SammiAlert(SammiBox):
    name = "alert"
    label = "SAMMI alert"
    help = "Shows a yellow alert message in SAMMI"
    group = "Messages"

    async def run(self, message: str) -> Any:
        return await self._sammi.send({"request": "alertMessage", "message": message})
