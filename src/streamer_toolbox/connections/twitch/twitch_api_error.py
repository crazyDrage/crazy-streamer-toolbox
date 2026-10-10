class TwitchApiError(RuntimeError):
    """Twitch answered a request with an error status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Twitch said {status}: {message}")
        self.status = status
