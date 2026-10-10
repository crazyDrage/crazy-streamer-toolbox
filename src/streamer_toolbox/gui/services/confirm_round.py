import asyncio
from typing import Optional


class ConfirmRound:
    """One yes/no question shown on several screens: the first answer wins, later ones are ignored."""

    def __init__(self) -> None:
        self._future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

    def answer(self, value: bool) -> bool:
        """Returns False if the round was already answered or timed out."""
        if self._future.done():
            return False
        self._future.set_result(value)
        return True

    async def wait(self, timeout: float) -> Optional[bool]:
        try:
            return await asyncio.wait_for(self._future, timeout)
        except asyncio.TimeoutError:
            return None
