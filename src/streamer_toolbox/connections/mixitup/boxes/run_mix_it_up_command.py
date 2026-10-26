from typing import Any

from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _viewer_platforms
from streamer_toolbox.core.data.box_value import to_bool


class RunMixItUpCommand(MixitupBox):
    name = "run_command"
    label = "Run Mix It Up command"
    help = "Runs a Mix It Up command or action group by its name"
    labels = {"ignore_requirements": "Ignore its requirements"}
    hints = {"arguments": "What follows the command, like typed after it in chat",
             "ignore_requirements": "Runs even when its cooldown, cost or role says no"}
    group = "Commands"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"command": self.command_groups, "platform": _viewer_platforms}

    async def run(self, command: str, arguments: str = "", platform: str = "Twitch",
                  ignore_requirements: bool = False) -> None:
        body: dict[str, Any] = {"Arguments": str(arguments)}
        if platform and platform != "Twitch":
            body["Platform"] = platform
        if to_bool(ignore_requirements):
            body["IgnoreRequirements"] = True
        await self._send("POST", f"commands/{await self.command_id(command)}", json=body)
