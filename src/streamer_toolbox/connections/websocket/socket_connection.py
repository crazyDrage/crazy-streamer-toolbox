import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError

log = logging.getLogger(__name__)

T = TypeVar("T")


class SocketConnection(ConnectionBase, ABC):
    """A connection over a websocket, with his rule (11-21) for every send: when a send fails while the
    connection counts as connected, the connection is restarted and the send goes once more. The status stays
    connected in between, so the trigger "Status change" gives no "on disconnect" for a hiccup. Only when the
    second try fails too does it count as disconnected. While it isn't connected there is one try only.

    A subclass says how its connection restarts (`_restart`), what a failed connection looks like
    (`gone_errors`) and how it is marked disconnected (`_lost`). Its boxes send through `_send_safely`."""

    gone_errors: tuple[type[BaseException], ...] = (ConnectionError,)  # failures that mean the program is gone

    @abstractmethod
    async def _restart(self) -> None:
        """Gets the connection going again after a failed send; raises one of `gone_errors` when it can't."""

    @abstractmethod
    def _lost(self, e: BaseException) -> NotConnectedError:
        """Marks the connection disconnected because of `e` and gives the error the box shows."""

    async def _send_safely(self, send: Callable[[], Awaitable[T]]) -> T:
        """Runs `send` under the rule above."""
        if not self._settings["enabled"]:
            raise NotConnectedError(f"{self.title} is switched off under Connections → {self.title}")
        try:
            return await send()
        except self.gone_errors as first:
            if not self._status.ok:
                raise self._lost(first) from None
            log.info("%s: a send failed (%s); connecting again and sending once more", self.title,
                     str(first) or type(first).__name__)
        try:
            await self._restart()
            return await send()
        except self.gone_errors as e:
            raise self._lost(e) from None
