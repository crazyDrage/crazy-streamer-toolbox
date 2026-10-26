from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.interfaces.sound_player import SoundPlayer


class StopAllSounds(Box):
    name = "stop_all"
    label = "Stop all sounds"
    help = "Stops every sound the toolbox is playing"
    group = "Play"

    def __init__(self, player: SoundPlayer) -> None:
        self._player = player

    async def run(self) -> int:
        """How many were stopped."""
        return await self._player.stop_all()
