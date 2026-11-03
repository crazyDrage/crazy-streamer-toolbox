from pathlib import Path

from streamer_toolbox.core.interfaces.sound_player import SoundPlayer


class FakeSoundPlayer(SoundPlayer):
    """Remembers what it was asked to play; every sound is 1.5 s long and plays until stop_all."""

    def __init__(self) -> None:
        self.played: list[tuple[Path, float, bool]] = []

    async def play(self, path: Path, volume: float = 1.0, wait: bool = False) -> float:
        self.played.append((path, volume, wait))
        return 1.5

    async def stop_all(self) -> int:
        stopped, self.played = len(self.played), []
        return stopped
