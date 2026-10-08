import asyncio
from collections.abc import Callable
from typing import Any

import websockets


class SocketMessageSender:
    """Opens a websocket, sends one text and closes it again: all the programs that only take named messages
    need (VNyan, Warudo). Nothing is kept open, so the program can be started and closed at any time."""

    def __init__(self, connect: Callable[..., Any] = websockets.connect, timeout: float = 5.0) -> None:
        self._connect = connect
        self._timeout = timeout

    async def send(self, url: str, text: str | None = None) -> None:
        """Sends `text` to the program at `url`; without a text it only looks whether the program answers.
        OSError / TimeoutError / a websockets error when it doesn't."""
        socket = await asyncio.wait_for(self._connect(url), self._timeout)
        try:
            if text is not None:
                await asyncio.wait_for(socket.send(text), self._timeout)
        finally:
            await socket.close()
