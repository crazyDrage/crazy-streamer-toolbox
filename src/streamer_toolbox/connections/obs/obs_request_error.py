class ObsRequestError(Exception):
    """An obs-websocket request was answered with a failure status."""

    def __init__(self, request_type: str, code: int, comment: str | None) -> None:
        super().__init__(f"{request_type} failed ({code}): {comment or 'no comment'}")
        self.request_type = request_type
        self.code = code
        self.comment = comment
