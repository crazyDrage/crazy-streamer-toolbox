from streamer_toolbox.connections.voicemod.boxes.voicemod_box import VoicemodBox


class StopVoicemodSounds(VoicemodBox):
    name = "stop_sounds"
    label = "Stop Voicemod sounds"
    help = "Stops every soundboard sound"
    group = "Soundboard"

    async def run(self) -> None:
        await self._ask("stopAllMemeSounds", {}, answered=False)
