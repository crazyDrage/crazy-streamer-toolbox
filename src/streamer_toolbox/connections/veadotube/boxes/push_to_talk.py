from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient
from streamer_toolbox.core.actions.fixed_choices import fixed_choices

SWITCH = ("on", "off", "toggle")


class PushToTalk(VeadotubeBox):
    name = "push_to_talk"
    label = "Push-to-talk"
    help = "Switches veadotube mini's push-to-talk (its microphone) on or off, or the other way round"
    hints = {"switch": "on, off, or toggle (the other way round)"}

    def __init__(self, client: VeadotubeClient) -> None:
        super().__init__(client)
        self.options = {"switch": fixed_choices(list(SWITCH))}

    async def run(self, switch: str = "toggle") -> None:
        switch = str(switch).strip().casefold()
        if switch not in SWITCH:
            raise ValueError(f"push-to-talk: on, off or toggle, not {switch!r}")
        if switch == "toggle":
            await self._client.push_to_talk("toggle")
        else:
            await self._client.push_to_talk("set", switch == "on")
