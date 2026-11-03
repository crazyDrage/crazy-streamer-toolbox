from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class ReleaseSammiButton(SammiBox):
    name = "release_button"
    label = "Release SAMMI button"
    help = "Releases a SAMMI button that is running (stops it)"
    group = "Buttons"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"button_id": self.buttons}

    async def run(self, button_id: str) -> Any:
        return await self._sammi.send({"request": "releaseButton", "buttonID": button_id})
