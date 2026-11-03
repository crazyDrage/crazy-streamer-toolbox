from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox, bgr

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class ChangeSammiButton(SammiBox):
    name = "modify_button"
    label = "Change SAMMI button"
    help = "Changes a SAMMI button's text and / or colour (#rrggbb); empty = keep"
    group = "Buttons"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"button_id": self.buttons}

    async def run(self, button_id: str, text: str = "", color: str = "") -> Any:
        body: dict[str, Any] = {"request": "modifyButton", "buttonID": button_id}
        if text:
            body["text"] = text
        if color:
            body["color"] = bgr(color)
        return await self._sammi.send(body)
