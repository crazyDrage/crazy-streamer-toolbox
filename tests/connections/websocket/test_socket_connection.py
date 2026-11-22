import unittest

from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from tests.fakes.fake_socket_connection import FakeSocketConnection


class TestSocketConnection(unittest.IsolatedAsyncioTestCase):
    async def _connected(self, fails: int) -> FakeSocketConnection:
        connection = FakeSocketConnection(fails)
        await connection.start()
        connection.states.clear()
        return connection

    async def test_a_failed_send_while_connected_restarts_and_goes_again_without_a_disconnect(self) -> None:
        connection = await self._connected(fails=1)
        self.assertEqual(await connection.send("wave"), "wave")
        self.assertEqual((connection.tries, connection.restarts, connection.sent), (2, 1, ["wave"]))
        self.assertEqual(connection.states, [])
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)

    async def test_a_second_failure_counts_as_disconnected(self) -> None:
        connection = await self._connected(fails=2)
        with self.assertRaisesRegex(NotConnectedError, "Fake: gone"):
            await connection.send("wave")
        self.assertEqual((connection.tries, connection.restarts, connection.sent), (2, 1, []))
        self.assertEqual(connection.states, [ConnectionState.ERROR])

    async def test_not_connected_means_one_try_and_no_restart(self) -> None:
        connection = await self._connected(fails=3)
        with self.assertRaises(NotConnectedError):
            await connection.send("one")
        with self.assertRaises(NotConnectedError):
            await connection.send("two")
        self.assertEqual((connection.tries, connection.restarts), (3, 1))
        self.assertEqual(await connection.send("three"), "three")

    async def test_switched_off_sends_nothing(self) -> None:
        connection = FakeSocketConnection(fails=0, enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off under Connections → Fake"):
            await connection.send("wave")
        self.assertEqual(connection.tries, 0)

    async def test_other_failures_are_not_sent_again(self) -> None:
        connection = await self._connected(fails=0)

        async def refused() -> None:
            connection.tries += 1
            raise ValueError("the program said no")

        with self.assertRaisesRegex(ValueError, "said no"):
            await connection._send_safely(refused)
        self.assertEqual((connection.tries, connection.restarts), (1, 0))


if __name__ == "__main__":
    unittest.main()
