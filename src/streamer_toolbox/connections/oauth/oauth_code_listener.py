import asyncio
from urllib.parse import parse_qs, urlsplit

PAGE = ("<!doctype html><meta charset=utf-8><title>streamer-toolbox</title>"
        "<body style='font-family:sans-serif;padding:2rem'><h2>{title}</h2><p>{text}</p>")


class OAuthCodeListener:
    """Catches the one browser visit a service (Twitch, YouTube) sends back after the login
    (http://localhost:<port>/?code=...), then stops listening. Only runs while a login is going on, so it
    doesn't block the port otherwise. service: the name in the texts the browser tab shows."""

    def __init__(self, host: str = "localhost", port: int = 17563, service: str = "Twitch") -> None:
        self._service = service
        self._host = host
        self._port = port
        self._server: asyncio.base_events.Server | None = None
        self._result: asyncio.Future | None = None
        self._state = ""

    @property
    def port(self) -> int:
        return self._server.sockets[0].getsockname()[1] if self._server else self._port

    async def start(self, state: str) -> None:
        """Starts listening (OSError if the port is taken, e.g. by another tool logging in right now)."""
        self._state = state
        self._result = asyncio.get_running_loop().create_future()
        self._server = await asyncio.start_server(self._visit, self._host, self._port)

    async def wait(self, timeout: float) -> str:
        """The code the service sent; TimeoutError if nobody logged in, PermissionError if the login was refused."""
        try:
            return await asyncio.wait_for(asyncio.shield(self._result), timeout)
        finally:
            await self.stop()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _visit(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request_line = (await asyncio.wait_for(reader.readline(), 5)).decode("latin-1")
            while (await asyncio.wait_for(reader.readline(), 5)) not in (b"\r\n", b"\n", b""):
                pass  # skip the headers
            target = request_line.split(" ")[1] if " " in request_line else "/"
            query = {k: v[0] for k, v in parse_qs(urlsplit(target).query).items()}
            title, text = self._outcome(query)
            body = PAGE.format(title=title, text=text).encode("utf-8")
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                         b"Content-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body)
            await writer.drain()
        except (asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            writer.close()

    def _outcome(self, query: dict[str, str]) -> tuple[str, str]:
        if self._result is None or self._result.done():
            return "Already done", "You can close this tab."
        if query.get("state") != self._state:
            return "Not from this login", "This link doesn't belong to the login the toolbox started."
        if "error" in query:
            self._result.set_exception(PermissionError(
                f"{self._service} login refused: {query.get('error_description') or query['error']}"))
            return "Login cancelled", f"The toolbox is not connected to {self._service}. You can close this tab."
        if "code" not in query:
            return "Nothing to do", "You can close this tab."
        self._result.set_result(query["code"])
        return f"{self._service} is connected", "The toolbox has its login. You can close this tab."
