from typing import Any
from urllib.parse import quote

from streamer_toolbox.connections.firebot.boxes.firebot_box import FirebotBox, Send, _find, _object


class RunFirebotEffectList(FirebotBox):
    name = "run_preset"
    label = "Run Firebot effect list"
    help = "Runs a preset effect list made in Firebot"
    hints = {"args": 'Optional: an object with the list\'s arguments, like {"user": "ann"}',
             "user": "Optional: the viewer the effects are run for",
             "wait": "Yes: the box waits until Firebot ran all effects"}

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"preset": self.preset_names}

    async def run(self, preset: str, args: Any = None, user: str = "", wait: bool = False) -> None:
        preset_id = _find(await self._by_name("effects/preset"), preset, "preset effect list")
        body = {"args": _object(args), **({"username": str(user)} if str(user).strip() else {})}
        await self._send("POST", f"effects/preset/{quote(preset_id)}" + ("" if wait else "/run"), json=body)
