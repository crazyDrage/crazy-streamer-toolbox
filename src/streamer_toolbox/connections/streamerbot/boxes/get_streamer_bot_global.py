from typing import Any

from streamer_toolbox.connections.streamerbot.boxes.streamerbot_box import StreamerbotBox


class GetStreamerBotGlobal(StreamerbotBox):
    name = "get_global"
    label = "Get Streamer.bot global"
    help = "The value of one of Streamer.bot's global variables"
    outputs = {"value": "text"}
    hints = {"persisted": "Yes: a variable Streamer.bot keeps over a restart"}

    async def run(self, variable: str, persisted: bool = True) -> dict[str, Any]:
        answer = await self._ask({"request": "GetGlobal", "variable": str(variable).strip(),
                                  "persisted": bool(persisted)})
        found = answer.get("variable") if isinstance(answer.get("variable"), dict) else {}
        return {"value": found.get("value", "")}
