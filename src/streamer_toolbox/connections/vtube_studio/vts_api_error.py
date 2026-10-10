class VtsApiError(Exception):
    """VTube Studio answered a request with an APIError (e.g. 50 = user denied the plugin)."""

    def __init__(self, request_type: str, error_id: int, message: str) -> None:
        super().__init__(f"{request_type} failed ({error_id}): {message}")
        self.request_type = request_type
        self.error_id = error_id
