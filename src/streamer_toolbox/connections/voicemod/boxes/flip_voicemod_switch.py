from streamer_toolbox.connections.voicemod.boxes.voicemod_box import VoicemodBox, Ask, TOGGLES


class FlipVoicemodSwitch(VoicemodBox):
    name = "toggle"
    label = "Flip Voicemod switch"
    help = "Flips one of Voicemod's switches; tells how it is now"
    outputs = {"on": "yes/no"}

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"switch": self.switches}

    async def run(self, switch: str) -> dict[str, bool]:
        action = TOGGLES.get(str(switch).strip())
        if action is None:
            raise ValueError(f"Which switch? One of {', '.join(TOGGLES)}")
        return {"on": bool((await self._ask(action, {})).get("value"))}
