from streamer_toolbox.connections.lumia.boxes.lumia_box import LumiaBox, Retrieve, Send, _named


class RunLumiaCommand(LumiaBox):
    name = "command"
    label = "Run Lumia command"
    help = "Runs one of Lumia Stream's commands, as if a viewer had typed it"
    hints = {"hold": "Yes: the lights stay like this (it becomes the default state)"}

    def __init__(self, send: Send, retrieve: Retrieve) -> None:
        super().__init__(send, retrieve)
        self.options = {"command": self.command_names}

    async def run(self, command: str, hold: bool = False) -> None:
        await self._send({"type": "chat-command", "params": {"value": _named(command, "command"),
                                                              **({"hold": True} if hold else {})}})
