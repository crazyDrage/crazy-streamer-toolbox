class YouTubeApiError(Exception):
    """Google refused a call: its HTTP status, its reason word (quotaExceeded, liveChatEnded, ...) and message."""

    def __init__(self, status: int, message: str, reason: str = "") -> None:
        super().__init__(f"{status}: {message}")
        self.status = status
        self.reason = reason
