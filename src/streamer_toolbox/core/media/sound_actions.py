from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.sound_player import SoundPlayer

SOUND_TYPES = (".ogg", ".mp3", ".wav", ".flac")


class SoundActions:
    """The Sound boxes: play a file (like SAMMI's Play Sound), stop everything. `folder` is where the file
    list in the editor comes from (his stream sounds); any full path works too."""

    def __init__(self, player: SoundPlayer, folder: Path | None = None) -> None:
        self._player = player
        self._folder = folder

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("sound.play", self.play, "Plays a sound file on this PC (volume 0 to 1). Wait = the flow goes "
                    "on when the sound ended", "Play sound", group="Play", options={"file": self.files},
                    files={"file": SOUND_TYPES})
        actions.add("sound.stop_all", self._player.stop_all, "Stops every sound the toolbox is playing",
                    "Stop all sounds", group="Play")

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
