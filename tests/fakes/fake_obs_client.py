import simpleobsws


class FakeObsClient:
    """Stands in for simpleobsws.WebSocketClient: records requests and answers from a dict."""

    def __init__(self, responses: dict[str, simpleobsws.RequestResponse]) -> None:
        self._responses = responses
        self.requests: list[simpleobsws.Request] = []

    async def call(self, request: simpleobsws.Request, timeout: int = 15) -> simpleobsws.RequestResponse:
        self.requests.append(request)
        return self._responses[request.requestType]
