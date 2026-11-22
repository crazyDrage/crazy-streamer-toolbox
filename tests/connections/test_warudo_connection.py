import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.warudo_connection import WarudoConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.inbox_types import InboxTypes
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from tests.fakes.fake_failing_sender import FakeFailingSender
from tests.fakes.fake_text_socket_server import FakeTextSocketServer


class TestWarudoConnection(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _actions(url: str, enabled: bool = True) -> tuple[WarudoConnection, ActionRegistry]:
        connection = WarudoConnection({"enabled": enabled, "url": url})
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    def test_it_is_off_until_switched_on(self) -> None:
        connection = WarudoConnection({})
        self.assertFalse(connection.settings["enabled"])
        self.assertEqual(connection.settings["url"], "ws://localhost:19190")

    async def test_an_action_goes_as_json_with_a_typed_number_as_a_number(self) -> None:
        async with FakeTextSocketServer() as server:
            connection, actions = self._actions(server.url)
            await connection.start()
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            await actions.run("warudo.send", action="Vibrate", data="80")
            await actions.run("warudo.send", action="Tilt", data="0.5")
            await actions.run("warudo.send", action="Say", data="hello there")
            await actions.run("warudo.send", action=" Wave ")
            for _ in range(150):
                if len(server.received) == 4:
                    break
                await asyncio.sleep(0.02)
            self.assertEqual([json.loads(text) for text in server.received], [
                {"action": "Vibrate", "data": 80}, {"action": "Tilt", "data": 0.5},
                {"action": "Say", "data": "hello there"}, {"action": "Wave"}])
            with self.assertRaises(ValueError):
                await actions.run("warudo.send", action="")

    async def test_a_raw_message_goes_as_it_is(self) -> None:
        async with FakeTextSocketServer() as server:
            connection, actions = self._actions(server.url)
            await connection.start()
            await actions.run("warudo.raw", message="wave")
            await actions.run("warudo.raw", message=' {"not": "touched"} ')
            for _ in range(150):
                if len(server.received) == 2:
                    break
                await asyncio.sleep(0.02)
            self.assertEqual(server.received, ["wave", ' {"not": "touched"} '])
            with self.assertRaises(ValueError):
                await actions.run("warudo.raw", message="")

    async def test_warudo_not_running_or_switched_off_is_said_plainly(self) -> None:
        async with FakeTextSocketServer() as server:
            gone = server.url
        connection, actions = self._actions(gone)
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertIn("is it running", connection.status.detail)
        with self.assertRaises(NotConnectedError):
            await actions.run("warudo.send", action="Wave")
        _, off = self._actions(gone, enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("warudo.send", action="Wave")

    async def _connected_with(self, sender: FakeFailingSender) -> tuple[WarudoConnection, ActionRegistry]:
        connection = WarudoConnection({"enabled": True}, sender=sender, again_after=0)
        actions = ActionRegistry()
        connection.add_actions(actions)
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
        return connection, actions

    async def test_a_failed_send_while_connected_is_sent_again_without_a_disconnect(self) -> None:
        sender = FakeFailingSender(fails=1)
        connection, actions = await self._connected_with(sender)
        states = []
        original = connection._set_status
        connection._set_status = lambda status: (states.append(status.state), original(status))
        await actions.run("warudo.raw", message="wave")
        self.assertEqual(sender.sent, ["wave"])
        self.assertEqual(sender.tries, 2)
        self.assertNotIn(ConnectionState.ERROR, states)
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)

    async def test_when_the_second_try_fails_too_it_counts_as_disconnected(self) -> None:
        sender = FakeFailingSender(fails=2)
        connection, actions = await self._connected_with(sender)
        with self.assertRaises(NotConnectedError):
            await actions.run("warudo.raw", message="wave")
        self.assertEqual(sender.tries, 2)
        self.assertEqual(sender.sent, [])
        self.assertEqual(connection.status.state, ConnectionState.ERROR)

    async def test_not_connected_means_one_try_only(self) -> None:
        sender = FakeFailingSender(fails=3)
        connection, actions = await self._connected_with(sender)
        with self.assertRaises(NotConnectedError):
            await actions.run("warudo.raw", message="one")  # tries 1 + 2: now disconnected
        with self.assertRaises(NotConnectedError):
            await actions.run("warudo.raw", message="two")  # try 3 only, no second one
        self.assertEqual(sender.tries, 3)
        await actions.run("warudo.raw", message="three")  # Warudo is back: connected again
        self.assertEqual(sender.sent, ["three"])
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)

    async def test_the_input_address_box_gives_the_address_with_the_key(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            events, key_file, types = _inbox_parts(Path(folder))
            connection = WarudoConnection({"enabled": True}, events=events, in_key=key_file,
                                          in_types=types, port=8899)
            actions = ActionRegistry()
            connection.add_actions(actions)
            key = connection.inbox().key()
            self.assertEqual(f"ws://127.0.0.1:8899/connections/warudo/in/camera?key={key}",
                             await actions.run("warudo.input_address", type="camera"))
            self.assertTrue(str(await actions.run("warudo.input_address")).endswith(f"/in/default?key={key}"))

    async def test_the_connection_gives_its_inbox_and_follows_its_switch(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            events, key_file, types = _inbox_parts(Path(folder))
            self.assertIsNone(WarudoConnection({}).inbox())
            connection = WarudoConnection({"enabled": False}, events=events, in_key=key_file,
                                          in_types=types)
            inbox = connection.inbox()
            key = inbox.key()
            self.assertIn("switched off", inbox.refusal(key))
            connection.configure({"enabled": True})
            self.assertEqual("", inbox.refusal(key))


def _inbox_parts(folder: Path) -> tuple[EventBus, SecretFile, InboxTypes]:
    return (EventBus(), SecretFile(folder / "secrets" / "warudo_in_key.txt", "key"),
            InboxTypes(folder / "inbox_types.json"))


if __name__ == "__main__":
    unittest.main()
