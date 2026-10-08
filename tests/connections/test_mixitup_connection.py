import unittest

import httpx

from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.connections.mixitup_connection import MixItUpConnection

COMMANDS = {"TotalCount": 2, "Commands": [{"ID": "id-hammer", "Name": "hammer_bong"},
                                          {"ID": "id-marker", "Name": "twitch_marker"}]}


class TestMixItUpConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.requests: list[httpx.Request] = []

    def _miu(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/status/version"):
            return httpx.Response(200, text="1.8.201.0")  # the real one answers text/plain
        if path.endswith("/commands"):
            return httpx.Response(200, json=COMMANDS)
        return httpx.Response(200)

    def _connection(self) -> MixItUpConnection:
        return MixItUpConnection({"enabled": True}, httpx.MockTransport(self._miu))

    async def test_start_shows_version_and_command_count(self) -> None:
        connection = self._connection()
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
        self.assertEqual(connection.status.facts, (("Mix It Up", "1.8.201.0"), ("Commands", "2")))

    async def test_unreachable_is_explained(self) -> None:
        def down(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)
        status = await MixItUpConnection({"enabled": True}, httpx.MockTransport(down)).test({"url": "http://localhost:8911/api/v2"})
        self.assertEqual(status.detail, "can't reach Mix It Up: is it running, with the Developer API on?")


if __name__ == "__main__":
    unittest.main()
