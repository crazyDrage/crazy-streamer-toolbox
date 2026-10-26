from typing import Any

from streamer_toolbox.connections.streamerbot.boxes.streamerbot_box import StreamerbotBox, Ask, _object


class RunStreamerBotAction(StreamerbotBox):
    name = "do_action"
    label = "Run Streamer.bot action"
    help = "Runs an action made in Streamer.bot"
    hints = {"args": 'Optional: an object like {"user": "ann"}; the action gets each as %user%'}

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"action": self.action_names}

    async def run(self, action: str, args: Any = None) -> None:
        action = str(action).strip()
        if not action:
            raise ValueError("Which action? Pick one made in Streamer.bot")
        await self._ask({"request": "DoAction", "action": {"name": action}, "args": _object(args)})
