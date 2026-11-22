import asyncio
import time
import unittest

from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer
from tests.fakes.fake_line_connection import FakeLineConnection


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


def echo(message: dict, path: str) -> dict | None:
    return {"ref": message["ref"], "you_said": message.get("say")} if "ref" in message else None


class TestLineConnection(unittest.IsolatedAsyncioTestCase):
    async def _started(self, url: str) -> FakeLineConnection:
        connection = FakeLineConnection(url)
        self.addAsyncCleanup(connection.stop)
        await connection.start()
        await until(lambda: connection.status.ok)
        return connection

    async def test_a_request_during_a_hiccup_waits_for_the_line_and_goes_without_a_disconnect(self) -> None:
        async with FakeJsonSocketServer(echo) as server:
            connection = await self._started(server.url)
            await server.drop()
            answer = await connection.ask({"say": "still here"})
            self.assertEqual(answer["you_said"], "still here")
            self.assertNotIn(ConnectionState.ERROR, connection.states)
            self.assertTrue(connection.status.ok)

    async def test_the_program_gone_is_said_plainly_and_shows_disconnected(self) -> None:
        async with FakeJsonSocketServer(echo) as server:
            connection = await self._started(server.url)
        with self.assertRaisesRegex(NotConnectedError, "Fake is not connected"):
            await connection.ask({"say": "anyone?"})
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("trying again", connection.status.detail)


if __name__ == "__main__":
    unittest.main()
