import unittest
from typing import Any

from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.connection_watcher import STATUS, ConnectionWatcher
from streamer_toolbox.core.events.event_bus import EventBus
from tests.fakes.fake_connection import FakeConnection


class TestConnectionWatcher(unittest.IsolatedAsyncioTestCase):
    """The trigger "Status change": once each time a connection gets connected or lost."""

    async def test_an_event_each_time_a_connection_gets_connected(self) -> None:
        events = EventBus()
        heard: list[tuple[str, dict[str, Any]]] = []

        async def hear(kind: str, data: dict[str, Any]) -> None:
            heard.append((kind, data))

        events.subscribe(hear)
        warudo, obs = _connection("warudo", "Warudo"), _connection("obs", "OBS")
        watcher = ConnectionWatcher(lambda: [warudo, obs], events)
        warudo._set_status(ConnectionStatus(ConnectionState.CONNECTED))  # came up with the toolbox
        watcher.check()
        watcher.check()  # still connected: nothing new
        warudo._set_status(ConnectionStatus(ConnectionState.ERROR, "closed"))
        watcher.check()
        warudo._set_status(ConnectionStatus(ConnectionState.CONNECTED))  # Warudo started again
        obs._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        watcher.check()
        await events.wait_idle()
        warudo._set_status(ConnectionStatus(ConnectionState.OFF))  # switched off
        watcher.check()
        await events.wait_idle()
        said = [(data["connection"], data["status"]) for kind, data in heard]
        self.assertEqual(said, [("warudo", "connected"), ("warudo", "disconnected"), ("warudo", "connected"),
                                ("warudo", "disconnected")])
        self.assertEqual({STATUS}, {kind for kind, _ in heard})
        self.assertEqual("Warudo", heard[0][1]["title"])


def _connection(connection_id: str, title: str) -> FakeConnection:
    connection = FakeConnection()
    connection.id, connection.title = connection_id, title
    return connection


if __name__ == "__main__":
    unittest.main()
