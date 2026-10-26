from typing import Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox


class SammiNotification(SammiBox):
    name = "notification"
    label = "SAMMI notification"
    help = "Shows a bubble notification from SAMMI (like its timer buttons do)"
    group = "Messages"

    async def run(self, message: str, title: str = "streamer-toolbox") -> Any:
        return await self._sammi.send({"request": "notificationMessage", "title": title, "message": message})
