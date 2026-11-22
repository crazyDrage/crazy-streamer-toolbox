import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.vnyan.vnyan_copy_texts import decode
from streamer_toolbox.connections.vnyan_connection import VNyanConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.inbox_types import InboxTypes
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.events.event_bus import EventBus
from tests.fakes.fake_failing_sender import FakeFailingSender
from tests.fakes.fake_text_socket_server import FakeTextSocketServer


class TestVNyanConnection(unittest.IsolatedAsyncioTestCase):
    def _actions(self, url: str, enabled: bool = True) -> tuple[VNyanConnection, ActionRegistry]:
        connection = VNyanConnection({"enabled": enabled, "url": url})
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    def test_it_is_off_until_switched_on(self) -> None:
        connection = VNyanConnection({})
        self.assertFalse(connection.settings["enabled"])
        self.assertEqual(connection.settings["url"], "ws://127.0.0.1:8000/vnyan")  # localhost may go to ::1 (11-22)
        self.assertNotIn("api", connection.settings)  # the API box went (11-22); a saved address is ignored
        self.assertNotIn("api", VNyanConnection({"api": "http://127.0.0.1:8069"}).settings)

    async def test_a_message_goes_as_plain_text_with_its_value_behind_it(self) -> None:
        async with FakeTextSocketServer("/vnyan") as server:
            connection, actions = self._actions(server.url)
            await connection.start()
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            self.assertEqual(server.received, [])  # looking whether it is there sends nothing
            await actions.run("vnyan.send", message="confetti")
            await actions.run("vnyan.send", message=" size ", value="0.5")
            await self._until(lambda: len(server.received) == 2)
            self.assertEqual(server.received, ["confetti", "size 0.5"])
            self.assertEqual(set(server.paths), {"/vnyan"})
            with self.assertRaises(ValueError):
                await actions.run("vnyan.send", message="  ")

    async def test_the_copy_buttons_give_vnyan_blocks_for_the_box(self) -> None:
        _, actions = self._actions("ws://127.0.0.1:1/vnyan")
        self.assertEqual("vnyan.text_block:Copy VNyan block", actions.get("vnyan.send").copies)
        self.assertEqual("vnyan.data_block:Copy VNyan block", actions.get("vnyan.data").copies)
        for hidden in ("vnyan.text_block", "vnyan.data_block"):
            self.assertFalse(actions.get(hidden).offered)
        text = decode(await actions.run("vnyan.text_block", message="test stuff"))
        self.assertIn("commandtest stuff", text)
        for data in ('{"command": "throw", "item": "tomato"}', {"command": "string", "item": "string"},
                     "command, item"):
            block = decode(await actions.run("vnyan.data_block", data=data))
            self.assertIn("opts2namek0commandk1item", block)

    async def test_vnyan_not_running_or_switched_off_is_said_plainly(self) -> None:
        async with FakeTextSocketServer("/vnyan") as server:
            gone = server.url
        connection, actions = self._actions(gone)
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertIn("is it running", connection.status.detail)
        with self.assertRaises(NotConnectedError):
            await actions.run("vnyan.send", message="confetti")
        _, off = self._actions(gone, enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("vnyan.send", message="confetti")
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("vnyan.data", data={"command": "throw"})

    async def test_it_is_green_again_after_a_message_got_through(self) -> None:
        async with FakeTextSocketServer("/vnyan") as server:
            connection, actions = self._actions(server.url)
            self.assertEqual(connection.status.state, ConnectionState.OFF)
            await actions.run("vnyan.send", message="confetti")
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)

    async def test_a_failed_send_while_connected_goes_once_more_before_it_counts_as_disconnected(self) -> None:
        for fails, sent, state in ((1, ["confetti"], ConnectionState.CONNECTED), (2, [], ConnectionState.ERROR)):
            sender = FakeFailingSender(fails)
            connection = VNyanConnection({"enabled": True}, sender=sender, again_after=0)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            if fails == 1:
                await actions.run("vnyan.send", message="confetti")
            else:
                with self.assertRaisesRegex(NotConnectedError, "Start Receiver on"):
                    await actions.run("vnyan.send", message="confetti")
            self.assertEqual((sender.tries, sender.sent, connection.status.state), (2, sent, state))

    async def test_data_goes_as_one_json_line_with_every_value_as_text(self) -> None:
        async with FakeTextSocketServer("/vnyan") as server:
            _, actions = self._actions(server.url)
            await actions.run("vnyan.data", data={"command": "throw", "count": 3, "item": "Tomate ♥"})
            await actions.run("vnyan.data", data='{"inner": {"a": 1}}')
            await self._until(lambda: len(server.received) == 2)
            self.assertEqual([json.loads(text) for text in server.received], [
                {"command": "throw", "count": "3", "item": "Tomate ♥"}, {"inner": '{"a": 1}'}])
            for empty in ({}, "", None):
                with self.assertRaisesRegex(ValueError, "Which values"):
                    await actions.run("vnyan.data", data=empty)
            with self.assertRaises(ValueError):
                await actions.run("vnyan.data", data="throw")

    async def test_messages_from_vnyan_come_in_with_the_key_in_a_127_address(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            events = EventBus()
            heard = []

            async def hear(kind, data) -> None:
                heard.append((kind, data))

            events.subscribe(hear)
            self.assertIsNone(VNyanConnection({}).inbox())
            connection = VNyanConnection({"enabled": True}, events=events, port=8899,
                                         in_key=SecretFile(Path(folder) / "vnyan_in_key.txt", "key"),
                                         in_types=InboxTypes(Path(folder) / "inbox_types.json"))
            inbox = connection.inbox()
            key = inbox.key()
            self.assertEqual(f"ws://127.0.0.1:8899/connections/vnyan/in/default?key={key}",
                             connection.in_address("default"))
            self.assertEqual("", inbox.refusal(key))
            self.assertIn("Connections → VNyan", inbox.refusal("wrong"))
            inbox.opened("default")
            inbox.received("default", '{"data": "test"}')
            inbox.received("default", "testing 9")
            await events.wait_idle()
            self.assertEqual(heard, [
                ("vnyan.message", {"type": "default", "text": '{"data": "test"}'}),
                ("vnyan.message", {"type": "default", "text": "testing 9"})])
            self.assertEqual(["default"], inbox.known_types())
            connection.configure({"enabled": False})
            self.assertIn("switched off", inbox.refusal(key))

    @staticmethod
    async def _until(check, tries: int = 150) -> None:
        for _ in range(tries):
            if check():
                return
            await asyncio.sleep(0.02)
        raise AssertionError("timed out")


if __name__ == "__main__":
    unittest.main()
