import simpleobsws


class FakeConnectableObsClient:
    """Stands in for simpleobsws.WebSocketClient including connect/identify, without a network."""

    def __init__(self, identifies: bool = True, reachable: bool = True,
                 responses: dict[str, dict] | None = None) -> None:
        self.url = "ws://fake:4455"
        self.identified = False
        self.ws_open = False
        self.connects = 0
        self.requests: list[str] = []
        self.calls: list[tuple[str, dict]] = []  # with their data
        self._identifies = identifies
        self._reachable = reachable
        self._responses = responses or {}

    async def connect(self) -> bool:
        if not self._reachable:
            raise ConnectionRefusedError("refused")
        self.connects += 1
        self.ws_open = True
        return True

    async def wait_until_identified(self, timeout: int = 10) -> bool:
        self.identified = self._identifies
        return self._identifies

    async def disconnect(self) -> bool:
        self.ws_open = False
        self.identified = False
        return True

    async def call(self, request: simpleobsws.Request, timeout: int = 15) -> simpleobsws.RequestResponse:
        self.requests.append(request.requestType)
        self.calls.append((request.requestType, request.requestData or {}))
        return simpleobsws.RequestResponse(request.requestType, simpleobsws.RequestStatus(True, 100),
                                          self._responses.get(request.requestType, {}))
