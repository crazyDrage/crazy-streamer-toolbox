from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class GetSammiVariable(SammiBox):
    name = "get_variable"
    label = "Get SAMMI variable"
    help = "Reads a SAMMI variable (global unless a button is picked)"
    group = "Variables"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"button_id": self.buttons_and_global}

    async def run(self, name: str, button_id: str = "global") -> Any:
        params = {"request": "getVariable", "name": name}
        if button_id and button_id != "global":
            params["buttonID"] = button_id
        return await self._sammi.get(**params)
