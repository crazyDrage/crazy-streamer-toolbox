import asyncio

import simpleobsws

from streamer_toolbox.connections.obs.obs_connection_error import ObsConnectionError


class LazyObsClient:
    """Wraps a simpleobsws client so it only connects on the first request, and reconnects after a drop.

    Starting the toolbox never touches OBS; only running an OBS action does.
    """

    def __init__(self, client: simpleobsws.WebSocketClient) -> None:
        self._client = client
        self._lock = asyncio.Lock()

    async def call(self, request: simpleobsws.Request, timeout: int = 15) -> simpleobsws.RequestResponse:
        async with self._lock:
            if not self._client.identified:
                await self._connect()
        return await self._client.call(request, timeout)

    async def _connect(self) -> None:
        if self._client.ws_open:
            await self._client.disconnect()
        try:
            await self._client.connect()
        except OSError as e:
            raise ObsConnectionError(f"can't reach OBS at {self._client.url}: {e}") from e
        if not await self._client.wait_until_identified():
            await self._client.disconnect()
            raise ObsConnectionError(f"OBS at {self._client.url} didn't identify us (password?)")
