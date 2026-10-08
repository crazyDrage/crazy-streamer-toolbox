from abc import ABC, abstractmethod

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition


class ModelMover(ABC):
    """Reads and moves the VTube Studio model (what an animation needs)."""

    @abstractmethod
    async def position(self) -> VtsPosition:
        """Where the loaded model is now."""

    @abstractmethod
    async def move(self, position: VtsPosition, seconds: float = 1.0) -> None:
        """Starts a move there taking seconds (0..2, 0 = jump); returns at once. A new move replaces a running one."""
