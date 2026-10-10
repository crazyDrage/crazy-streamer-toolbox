from abc import ABC, abstractmethod
from typing import Optional


class ConfirmService(ABC):
    """Asks the streamer a yes/no question, e.g. before an action Kit or a timer wants to run."""

    @abstractmethod
    async def ask(self, question: str, timeout: float = 20.0) -> Optional[bool]:
        """True/False from the first answer, None if nobody answered in time or no GUI is open."""
