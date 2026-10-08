from typing import Optional

from streamer_toolbox.core.interfaces.confirm_service import ConfirmService


class FakeConfirmService(ConfirmService):
    """Answers every question with the answer it was given, and remembers what was asked."""

    def __init__(self, answer: Optional[bool]) -> None:
        self.answer = answer
        self.asked: list[tuple[str, float]] = []

    async def ask(self, question: str, timeout: float = 20.0) -> Optional[bool]:
        self.asked.append((question, timeout))
        return self.answer
