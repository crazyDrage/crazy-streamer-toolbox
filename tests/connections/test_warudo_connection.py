import asyncio
import json
import unittest

from streamer_toolbox.connections.warudo_connection import WarudoConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
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


if __name__ == "__main__":
    unittest.main()
