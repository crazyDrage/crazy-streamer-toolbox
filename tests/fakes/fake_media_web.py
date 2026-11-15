import httpx

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 100


class FakeMediaWeb:
    """The web for the media buffer's tests: address -> (status, content type, body, extra headers); what was
    asked is in `asked`. An address it doesn't know answers 404. `resolve` is its name book: a name in `names`
    has those IP addresses, any other one is somewhere on the internet."""

    def __init__(self) -> None:
        self.pages: dict[str, tuple[int, str, bytes, dict[str, str]]] = {}
        self.asked: list[str] = []
        self.names: dict[str, list[str]] = {}
        self.transport = httpx.MockTransport(self._answer)

    def picture(self, url: str, body: bytes = PNG, kind: str = "image/png") -> None:
        self.pages[url] = (200, kind, body, {})

    async def resolve(self, host: str) -> list[str]:
        return self.names.get(host, ["93.184.215.14"])

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(str(request.url))
        status, kind, body, extra = self.pages.get(str(request.url), (404, "text/plain", b"not here", {}))
        return httpx.Response(status, headers={"content-type": kind, **extra}, content=body)
