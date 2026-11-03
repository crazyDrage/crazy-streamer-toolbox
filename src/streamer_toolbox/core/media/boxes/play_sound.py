from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.media.boxes.sound_shared import SOUND_TYPES

if TYPE_CHECKING:
    from streamer_toolbox.core.media.sound_actions import SoundActions


class PlaySound(Box):
    name = "play"
    label = "Play sound"
    help = "Plays a sound file on this PC (volume 0 to 1). Wait = the flow goes on when the sound ended"
    group = "Play"
    files = {"file": SOUND_TYPES}

    def __init__(self, sound: "SoundActions") -> None:
        self._sound = sound
        self.options = {"file": self._sound.files}

    async def run(self, file: str, volume: float = 1.0, wait: bool = False) -> float:
        return await self._sound.play(file, volume, wait)
