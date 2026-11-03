from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, STATES, Send, _states


class CommandOnOff(MixitupBox):
    name = "set_command"
    label = "Command on / off"
    help = "Switches a Mix It Up command on, off or the other way"
    group = "Commands"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"command": self.command_groups, "state": _states}

    async def run(self, command: str, state: str = "on") -> None:
        if state not in STATES:
            raise ValueError(f"state is on, off or toggle, not {state!r}")
        await self._send("PATCH", f"commands/{await self.command_id(command)}/state/{STATES[state]}")
