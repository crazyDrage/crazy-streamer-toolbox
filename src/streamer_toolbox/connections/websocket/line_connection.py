import asyncio
from collections.abc import Callable
from typing import Any

import websockets

from streamer_toolbox.connections.websocket.answer_lost_error import AnswerLostError
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.connections.websocket.socket_connection import SocketConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError


class LineConnection(SocketConnection):
    """A connection that keeps one websocket open (RequestSocket) and connects again by itself while the
    program isn't there; a line that drops is opened again once at once without showing disconnected. A
    subclass says where the program listens (`_url`), what to do after each connect (`_opened`: log in,
    subscribe) and what to do with a message the program sends by itself (`_message`). Its boxes ask through
    `_ask`: a send that fails while connected opens the line again and goes once more (SocketConnection), and
    it says plainly when the connection is off or the program is gone."""

    id_key = "id"  # where this program's requests carry their id
    gone_errors = (ConnectionError, websockets.ConnectionClosed)

    def __init__(self, defaults: dict[str, Any], settings: dict[str, Any],
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 beat: tuple[float, dict[str, Any] | str] | None = None, again_after: float = 0.5) -> None:
        super().__init__(defaults, settings)
        self._connect = connect
        self._retry_delay = retry_delay
        self._line = RequestSocket(self.title, lambda: self._url(self._settings), self._message, self._opened,
                                   self._state, self.id_key, self._reply_id, connect, retry_delay, beat=beat,
                                   hide=self._hide, again_after=again_after)
        self._tasks: list[asyncio.Task] = []

    def _url(self, settings: dict[str, Any]) -> str:
        """The websocket address for these settings; ValueError with words while something is missing."""
        raise NotImplementedError

    async def _opened(self, line: RequestSocket) -> None:
        """After each connect. PermissionError = the program refused the key: no more tries."""

    async def _message(self, message: dict[str, Any]) -> None:
        """A message the program sent by itself."""

    def _reply_id(self, message: dict[str, Any]) -> Any:
        return message.get(self.id_key)

    def _hide(self, text: str) -> str:
        """`text` without this connection's secret."""
        return text

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return ()

    def _more_lines(self) -> list[RequestSocket]:
        """Further websockets that run alongside (a program with a second address for its events)."""
        return []

    async def start(self) -> None:
        await self.stop()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        self._tasks = [asyncio.create_task(line.run()) for line in (self._line, *self._more_lines())]

    async def stop(self) -> None:
        tasks, self._tasks = self._tasks, []
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Connects once: says whether the program is there. Sends nothing."""
        socket = None
        try:
            socket = await asyncio.wait_for(self._connect(self._url(settings)), 5)
        except ValueError as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, f"can't reach {self.title} "
                                                           f"({self._hide(str(e) or type(e).__name__)})")
        finally:
            if socket is not None:
                await socket.close()
        return ConnectionStatus(ConnectionState.CONNECTED)

    async def _ask(self, message: dict[str, Any], answered: bool = True) -> dict[str, Any]:
        """Sends a request and gives the answer; with answered=False it only sends (for requests the program
        doesn't answer) and gives {}. A request whose answer was lost with the line is not sent again: the
        program may have done it already."""
        async def ask() -> dict[str, Any]:
            if answered:
                return await self._line.request(message)
            await self._line.send(message)
            return {}

        try:
            return await self._send_safely(ask)
        except AnswerLostError as e:
            raise NotConnectedError(f"{self.title}: {e}") from None

    async def _restart(self) -> None:
        await self._line.reopen()

    def _lost(self, e: BaseException) -> NotConnectedError:
        """The line says itself when it is down (its own tries go on), so only the box's error is made here."""
        return NotConnectedError(f"{self.title} is not connected ({self._status.detail or 'is it running?'})")

    def _state(self, text: str) -> None:
        if text == "connected":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", self._facts()))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))
