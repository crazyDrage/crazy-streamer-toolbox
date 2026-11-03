from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class SetSammiVariable(SammiBox):
    name = "set_variable"
    label = "Set SAMMI variable"
    help = "Sets a SAMMI variable (global unless a button is picked)"
    group = "Variables"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"button_id": self.buttons_and_global}

    async def run(self, name: str, value: str, button_id: str = "global") -> Any:
        return await self._sammi.send({"request": "setVariable", "name": name, "value": value, "buttonID": button_id})
