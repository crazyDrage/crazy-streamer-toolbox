class FakeFailingSender:
    """Stands in for SocketMessageSender: the first `fails` sends with a text raise OSError (the program went
    away), later ones work. A look without a text always works. Every text that got through is in `sent`."""

    def __init__(self, fails: int) -> None:
        self.fails = fails
        self.tries = 0
        self.sent: list[str] = []

    async def send(self, url: str, text: str | None = None) -> None:
        if text is None:
            return
        self.tries += 1
        if self.tries <= self.fails:
            raise OSError("connection refused")
        self.sent.append(text)
