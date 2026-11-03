from streamer_toolbox.connections.voicemod.boxes.voicemod_box import VoicemodBox, Ask, NO_EFFECT, _find


class SetVoicemodVoice(VoicemodBox):
    name = "voice"
    label = "Set Voicemod voice"
    help = "Switches Voicemod to a voice"

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"voice": self.voice_names}

    async def run(self, voice: str) -> None:
        wanted = str(voice).strip()
        voice_id = "nofx" if wanted.casefold() in (NO_EFFECT.casefold(), "nofx") \
            else _find(await self._voices(), wanted, "voice")
        await self._ask("loadVoice", {"voiceID": voice_id}, answered=False)
