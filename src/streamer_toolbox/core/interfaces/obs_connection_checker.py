from abc import ABC, abstractmethod

from streamer_toolbox.connections.obs.obs_status import ObsStatus


class ObsConnectionChecker(ABC):
    """Connects to OBS once, reads who it is, disconnects. Read-only: never changes anything in OBS."""

    @abstractmethod
    async def check(self, url: str, password: str) -> ObsStatus:
        """Raises ObsConnectionError when OBS can't be reached or refuses the password."""
