import asyncio
from typing import Any

from streamer_toolbox.connections.websocket.socket_connection import SocketConnection
from streamer_toolbox.connections.websocket.socket_message_sender import SocketMessageSender
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError


class VisitConnection(SocketConnection):
    """A program that only takes messages (VNyan, Warudo): nothing is kept open, every message is its own short
    visit to the websocket under the setting "url". So the program can be started and closed at any time, and
    a failed send is restarted by visiting again after `again_after` seconds."""

    retry_when_down = True
    gone_errors = (Exception,)  # whatever stops a visit: refused, timed out, a websockets error

    def __init__(self, defaults: dict[str, Any], settings: dict[str, Any],
                 sender: SocketMessageSender | None = None, again_after: float = 0.5) -> None:
        super().__init__(defaults, settings)
        self._sender = sender or SocketMessageSender()
        self._again_after = again_after

    def _reason(self, e: BaseException) -> str:
        """`e` in words for the tab and the box."""
        if isinstance(e, (OSError, TimeoutError)):
            return f"can't reach {self.title}: is it running?"
        return str(e) or type(e).__name__

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Looks whether the program's websocket answers. Sends nothing."""
        try:
            await self._sender.send(str(settings["url"]))
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, self._reason(e))
        return self._connected(settings)

    async def _send_text(self, text: str) -> None:
        url = str(self._settings["url"])
        await self._send_safely(lambda: self._sender.send(url, text))
        self._set_status(self._connected(self._settings))

    async def _restart(self) -> None:
        await asyncio.sleep(self._again_after)  # every visit is new: visiting again is the restart

    def _lost(self, e: BaseException) -> NotConnectedError:
        self._set_status(ConnectionStatus(ConnectionState.ERROR, self._reason(e)))
        return NotConnectedError(f"{self.title}: {self._reason(e)}")

    @staticmethod
    def _connected(settings: dict[str, Any]) -> ConnectionStatus:
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Websocket", str(settings["url"])),))
