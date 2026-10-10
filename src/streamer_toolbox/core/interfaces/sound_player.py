from abc import ABC, abstractmethod
from pathlib import Path


class SoundPlayer(ABC):
    """Plays sound files on this PC's default output, several at once if asked."""

    @abstractmethod
    async def play(self, path: Path, volume: float = 1.0, wait: bool = False) -> float:
        """Starts the sound (volume 0..1) and returns its length in seconds; with wait, returns when it ended."""

    @abstractmethod
    async def stop_all(self) -> int:
        """Stops every sound still playing; how many were stopped."""
