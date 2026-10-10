import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.connections.veadotube.veadotube_client import parse, url
from streamer_toolbox.connections.veadotube.veadotube_instances import VeadotubeInstances
from streamer_toolbox.connections.veadotube_connection import VeadotubeConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_veadotube_server import FakeVeadotubeServer


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestVeadotubeConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _instance(self, name: str, server: str, age: float = 0.0) -> None:
        (self.folder / name).write_text(json.dumps({"time": time.time() - age, "name": "veadotube mini",
                                                    "server": server}), encoding="utf-8")

    def _connection(self, **settings) -> tuple[VeadotubeConnection, ActionRegistry]:
        connection = VeadotubeConnection({"enabled": True, **settings}, self.events,
                                         VeadotubeInstances(self.folder), retry_delay=0.05)
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    def test_the_running_program_is_found_by_its_newest_fresh_file(self) -> None:
        instances = VeadotubeInstances(self.folder)
        self.assertEqual(instances.address(), "")
        self._instance("mini-0000000000000001-00000001", "127.0.0.1:1111", age=60)  # a program that is gone
        self._instance("veado-0000000000000002-00000002", "127.0.0.1:2222")         # not a mini
        (self.folder / "mini-0000000000000003-00000003").write_text("not json", encoding="utf-8")
        self.assertEqual(instances.address(), "")
        self._instance("mini-0000000000000004-00000004", "127.0.0.1:4444", age=3)
        self._instance("mini-0000000000000005-00000005", "127.0.0.1:5555", age=1)
        self.assertEqual(instances.address(), "127.0.0.1:5555")
        self.assertEqual(VeadotubeInstances(self.folder / "missing").address(), "")

    def test_the_address_gets_the_clients_name_and_frames_are_read_by_their_channel(self) -> None:
        self.assertEqual(url("127.0.0.1:2424"), "ws://127.0.0.1:2424?n=streamer-toolbox")
        self.assertEqual(url("ws://pc:1/?a=1"), "ws://pc:1/?a=1&n=streamer-toolbox")
        self.assertEqual(parse('nodes: {"event": "list"}'), {"event": "list"})
        self.assertEqual(parse(b'nodes:{"event": "list"}\x00'), {"event": "list"})
        self.assertEqual(parse('instance: {"event": "info"}'), {})
        self.assertEqual(parse("nodes: nonsense"), {})

    async def test_it_is_off_until_switched_on_and_says_when_no_veadotube_runs(self) -> None:
        self.assertFalse(VeadotubeConnection({}, self.events).settings["enabled"])
        connection, actions = self._connection()
        self.assertEqual((await connection.test(connection.settings)).detail, "no running veadotube mini found")
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("no running veadotube mini found", connection.status.detail)
        with self.assertRaises(ConnectionError):
            await actions.run("veadotube.set_state", state="happy")
        self.assertEqual(await actions.get("veadotube.set_state").options["state"](), [])
        await connection.stop()
        self.assertEqual(connection.status.state, ConnectionState.OFF)

    async def test_states_are_switched_by_name_and_a_change_starts_flows(self) -> None:
        async with FakeVeadotubeServer() as server:
            self._instance("mini-0000000000000001-00000001", server.address)
            connection, actions = self._connection()
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertTrue(server.paths[0].endswith("?n=streamer-toolbox"))
            await until(lambda: len(server.received) == 4)  # nodes, states, listen, peek
            self.assertEqual(await actions.get("veadotube.set_state").options["state"](),
                             ["idle", "happy", "angry"])
            self.assertEqual(await actions.run("veadotube.get_state"), {"state": "idle"})
            await actions.run("veadotube.set_state", state="Happy")  # upper / lower case doesn't matter
            await until(lambda: len(self.seen) == 1)
            kind, data = self.seen[0]
            self.assertEqual((kind, data), ("veadotube.state", {"state": "happy", "state_id": "2",
                                                                "previous": "idle"}))
            self.assertEqual(set(data), set(EVENT_FIELDS[kind]))  # what the Start box offers is what comes
            await actions.run("veadotube.show_state", state="angry", seconds=0.05)
            await until(lambda: len(self.seen) == 3)
            self.assertEqual([d["state"] for _, d in self.seen], ["happy", "angry", "happy"])  # and back
            await actions.run("veadotube.toggle_state", state="idle")
            await until(lambda: server.shown == "idle")
            await actions.run("veadotube.toggle_state", state="idle")
            await until(lambda: server.shown == "happy")
            await actions.run("veadotube.push_state", state="angry")
            await actions.run("veadotube.pop_state", state="angry")
            await until(lambda: len(self.seen) == 7)
            self.assertEqual(server.stack, ["2"])
            with self.assertRaisesRegex(KeyError, "no state named"):
                await actions.run("veadotube.set_state", state="sleepy")
            server.states["4"] = "sleepy"  # the avatar got a new state: found by asking again
            await actions.run("veadotube.set_state", state="sleepy")
            await until(lambda: server.shown == "sleepy")
            await connection.stop()

    async def test_a_typed_address_wins_and_it_connects_again_when_veadotube_comes_back(self) -> None:
        async with FakeVeadotubeServer() as server:
            self._instance("mini-0000000000000001-00000001", "127.0.0.1:1")
            connection, _ = self._connection(address=server.address)
            tried = await connection.test(connection.settings)
            self.assertEqual((tried.state, tried.facts), (ConnectionState.CONNECTED, (("Address", server.address),)))
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("trying again", connection.status.detail)
        async with FakeVeadotubeServer() as again:
            connection.configure({"enabled": True, "address": again.address})
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
        await connection.stop()


if __name__ == "__main__":
    unittest.main()
