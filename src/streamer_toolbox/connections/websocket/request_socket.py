import asyncio
import json
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

log = logging.getLogger(__name__)


class RequestSocket:
    """One websocket that stays open and talks JSON: requests that get an answer, and messages the program
    sends by itself. What the local programs with a websocket API have in common (Streamer.bot, T.I.T.S.,
    Voicemod, ...) and the services that only tell (Lumia Stream, Pulsoid, HypeRate).

    A request gets an id under `id_key`; the message whose `reply_id` is that id is its answer, every other
    message goes to on_message. After each connect on_open(self) runs (log in, subscribe; it may use
    request); once it is through, on_state gets "connected". A PermissionError from on_open (a refused key)
    stops it for good; anything else is tried again, slower each time. `beat` = (seconds, message) is sent
    again and again while connected, for servers that drop a quiet client. `hide` takes secrets out of a
    text before it is shown."""

    def __init__(self, name: str, url: Callable[[], str],
                 on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
                 on_open: Callable[["RequestSocket"], Awaitable[None]] | None = None,
                 on_state: Callable[[str], None] = lambda text: None, id_key: str = "id",
                 reply_id: Callable[[dict[str, Any]], Any] | None = None,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 timeout: float = 5.0, beat: tuple[float, dict[str, Any]] | None = None,
                 hide: Callable[[str], str] = lambda text: text) -> None:
        self._name = name
        self._url = url
        self._on_message = on_message
        self._on_open = on_open
        self._on_state = on_state
        self._id_key = id_key
        self._reply_id = reply_id or (lambda message: message.get(id_key))
        self._connect = connect
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._beat = beat
        self._hide = hide
        self._socket: Any = None
        self._waiting: dict[str, asyncio.Future] = {}
        self._failed: Exception | None = None
        self._delay = retry_delay

    @property
    def connected(self) -> bool:
        return self._socket is not None

    async def run(self) -> None:
        """Runs until cancelled, or until the program refuses the key."""
        self._delay = self._retry_delay
        while True:
            opener = None
            try:
                self._failed = None
                self._socket = await asyncio.wait_for(self._connect(self._url()), self._timeout)
                opener = asyncio.create_task(self._opened())
                async for frame in self._socket:
                    await self._handle(frame)
                raise self._failed or ConnectionError(f"{self._name} closed the line")
            except asyncio.CancelledError:
                await self._close(opener)
                raise
            except PermissionError as e:
                self._on_state(self._hide(str(e)))
                await self._close(opener)
                return
            except Exception as e:
                reason = self._hide(str(e) or type(e).__name__)
                log.info("%s: %s; trying again in %.0f s", self._name, reason, self._delay)
                self._on_state(f"{reason}; trying again in {self._delay:.0f} s")
                await self._close(opener)
                await asyncio.sleep(self._delay)
                self._delay = min(self._delay * 2, 60)

    async def request(self, message: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        """Sends `message` with a fresh id and gives the answer. ConnectionError while the line is down,
        TimeoutError when no answer comes."""
        if self._socket is None:
            raise ConnectionError(f"{self._name} is not connected")
        key = secrets.token_hex(6)
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._waiting[key] = future
        try:
            await self._socket.send(json.dumps({**message, self._id_key: key}, ensure_ascii=False))
            return await asyncio.wait_for(future, timeout or self._timeout)
        except TimeoutError:
            raise TimeoutError(f"{self._name} didn't answer") from None
        finally:
            self._waiting.pop(key, None)

    async def send(self, message: dict[str, Any]) -> None:
        """Sends `message` as it is, for things that get no answer. ConnectionError while the line is down."""
        if self._socket is None:
            raise ConnectionError(f"{self._name} is not connected")
        await self._socket.send(json.dumps(message, ensure_ascii=False))

    async def _opened(self) -> None:
        try:
            if self._on_open is not None:
                await self._on_open(self)
        except Exception as e:  # the reading loop above tells it and decides whether to try again
            self._failed = e
            await self._socket.close()
            return
        self._delay = self._retry_delay
        self._on_state("connected")
        while self._beat is not None:
            await asyncio.sleep(self._beat[0])
            await self.send(self._beat[1])

    async def _close(self, opener: asyncio.Task | None) -> None:
        socket, self._socket = self._socket, None
        if opener is not None:
            opener.cancel()
            await asyncio.gather(opener, return_exceptions=True)
        for future in self._waiting.values():
            if not future.done():
                future.set_exception(ConnectionError(f"{self._name} closed the line"))
        if socket is not None:
            await socket.close()

    async def _handle(self, frame: Any) -> None:
        try:
            message = json.loads(frame)
        except (ValueError, TypeError):
            return
        if not isinstance(message, dict):
            return
        waiting = self._waiting.get(str(self._reply_id(message) or ""))
        if waiting is not None:
            if not waiting.done():
                waiting.set_result(message)
        elif self._on_message is not None:
            try:
                await self._on_message(message)
            except Exception:
                log.exception("%s: a message could not be handled", self._name)
