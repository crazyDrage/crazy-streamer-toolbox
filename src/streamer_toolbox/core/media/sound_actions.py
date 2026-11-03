from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.sound_player import SoundPlayer
from streamer_toolbox.core.media.boxes.play_sound import PlaySound
from streamer_toolbox.core.media.boxes.sound_shared import SOUND_TYPES
from streamer_toolbox.core.media.boxes.stop_all_sounds import StopAllSounds


class SoundActions:
    """The Sound boxes: play a file (like SAMMI's Play Sound), stop everything. `folder` is where the file
    list in the editor comes from (his stream sounds); any full path works too."""

    def __init__(self, player: SoundPlayer, folder: Path | None = None) -> None:
        self._player = player
        self._folder = folder

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (PlaySound(self), StopAllSounds(self._player)):
            actions.add_box(box, "sound")

    async def play(self, file: str, volume: float = 1.0, wait: bool = False) -> float:
        path = Path(file)
        if not path.is_absolute() and self._folder is not None:
            path = self._folder / path
        return round(await self._player.play(path, float(volume), bool(wait)), 2)

    async def files(self) -> list[str]:
        if self._folder is None or not self._folder.is_dir():
            return []
        return sorted(str(p.relative_to(self._folder)) for p in self._folder.rglob("*")
                      if p.suffix.casefold() in SOUND_TYPES)
