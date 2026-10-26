from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class PressSammiButton(SammiBox):
    name = "trigger_button"
    label = "Press SAMMI button"
    help = "Presses a SAMMI button (the list is read from SAMMI each time; pick a deck first to narrow it)"
    group = "Buttons"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"button_id": self.buttons}

    async def run(self, button_id: str) -> Any:
        return await self._sammi.send({"request": "triggerButton", "buttonID": button_id})
