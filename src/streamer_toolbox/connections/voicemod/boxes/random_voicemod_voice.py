from streamer_toolbox.connections.voicemod.boxes.voicemod_box import VoicemodBox, Ask, RANDOM


class RandomVoicemodVoice(VoicemodBox):
    name = "random_voice"
    label = "Random Voicemod voice"
    help = "Switches Voicemod to a random voice"

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"among": self.random_kinds}

    async def run(self, among: str = "AllVoices") -> None:
        if among not in RANDOM:
            raise ValueError(f"Among which voices? One of {', '.join(RANDOM)}")
        await self._ask("selectRandomVoice", {"mode": among}, answered=False)
