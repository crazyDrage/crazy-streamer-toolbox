import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.connections.connection_state import ConnectionState
from tests.fakes.fake_connection import FakeConnection


class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "toolbox.toml"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _saved(self) -> dict:
        return ToolboxConfig.read(self.path).tables.get("fake", {})

    async def test_a_connection_nobody_switched_on_stays_off(self) -> None:
        connection = FakeConnection({"url": "good"})
        await ConnectionManager([connection], ConfigTableWriter(self.path)).start_all()
        self.assertEqual((connection.status.state, connection.calls), (ConnectionState.OFF, []))

    async def test_start_all_starts_only_enabled(self) -> None:
        on, off = FakeConnection({"url": "good", "enabled": True}), FakeConnection({"url": "good", "enabled": False})
        off.id = "fake_off"
        await ConnectionManager([on, off], ConfigTableWriter(self.path)).start_all()
        self.assertEqual((on.calls, off.calls), (["start"], []))
        self.assertEqual((on.status.state, off.status.state), (ConnectionState.CONNECTED, ConnectionState.OFF))

    async def test_connect_saves_switches_on_and_reconnects(self) -> None:
        connection = FakeConnection({"enabled": False, "password": "old"})
        status = await ConnectionManager([connection], ConfigTableWriter(self.path)).connect(
            "fake", {"url": "good", "password": ""})
        self.assertTrue(status.ok)
        self.assertEqual(self._saved(), {"enabled": True, "url": "good", "password": "old"})  # empty kept old
        self.assertEqual(connection.calls, ["test", "stop", "start"])

    async def test_failed_connect_changes_nothing(self) -> None:
        connection = FakeConnection({"url": "good", "enabled": True})
        status = await ConnectionManager([connection], ConfigTableWriter(self.path)).connect("fake", {"url": "bad"})
        self.assertEqual((status.state, status.detail), (ConnectionState.ERROR, "bad url"))
        self.assertFalse(self.path.exists())
        self.assertEqual((connection.calls, connection.settings["url"]), (["test"], "good"))

    async def test_switch_off_and_on(self) -> None:
        connection = FakeConnection({"url": "good", "enabled": True})
        manager = ConnectionManager([connection], ConfigTableWriter(self.path))
        await manager.set_enabled("fake", False)
        self.assertEqual((connection.status.state, self._saved()), (ConnectionState.OFF, {"enabled": False}))
        await manager.set_enabled("fake", True)
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
        self.assertEqual(connection.calls, ["stop", "stop", "start"])

    async def test_check_all_connects_a_program_started_later(self) -> None:
        connection = FakeConnection({"url": "bad", "enabled": True})
        connection.retry_when_down = True
        manager = ConnectionManager([connection], ConfigTableWriter(self.path))
        await manager.start_all()
        connection.configure({"url": "good", "enabled": True})  # the program is up now
        await manager.check_all()
        await manager.stop_all()
        self.assertEqual(connection.calls, ["start", "start", "stop"])

    async def test_check_all_leaves_connected_off_and_non_retrying_ones_alone(self) -> None:
        up, once = FakeConnection({"url": "good", "enabled": True}), FakeConnection({"url": "bad", "enabled": True})
        off = FakeConnection({"url": "bad", "enabled": False})
        off.id, once.id = "fake_off", "fake_once"
        up.retry_when_down = off.retry_when_down = True
        manager = ConnectionManager([up, off, once], ConfigTableWriter(self.path))
        await manager.start_all()
        await manager.check_all()
        await manager.stop_all()
        self.assertEqual((up.calls, off.calls, once.calls), (["start", "stop"], ["stop"], ["start", "stop"]))

    async def test_watcher_checks_by_itself(self) -> None:
        connection = FakeConnection({"url": "bad", "enabled": True})
        connection.retry_when_down = True
        manager = ConnectionManager([connection], ConfigTableWriter(self.path), check_every=0.01)
        await manager.start_all()
        await asyncio.sleep(0.05)
        await manager.stop_all()
        self.assertGreater(connection.calls.count("start"), 1)


if __name__ == "__main__":
    unittest.main()
