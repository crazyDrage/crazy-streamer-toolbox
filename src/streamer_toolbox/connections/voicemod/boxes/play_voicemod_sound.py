from streamer_toolbox.connections.voicemod.boxes.voicemod_box import VoicemodBox, Ask, _find


class PlayVoicemodSound(VoicemodBox):
    name = "play_sound"
    label = "Play Voicemod sound"
    help = "Plays a sound of Voicemod's soundboard"
    group = "Soundboard"

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"sound": self.sound_names}

    async def run(self, sound: str) -> None:
        file_name = _find(await self._sounds(), sound, "sound")
        await self._ask("playMeme", {"FileName": file_name, "IsKeyDown": True}, answered=False)
