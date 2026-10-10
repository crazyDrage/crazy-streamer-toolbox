from streamer_toolbox.core.interfaces.message_service import MessageService


class FakeMessageService(MessageService):
    """Remembers the messages instead of showing them; pretends one screen is open."""

    def __init__(self) -> None:
        self.shown: list[tuple[str, str]] = []

    async def show(self, message: str, title: str = "") -> int:
        self.shown.append((message, title))
        return 1
