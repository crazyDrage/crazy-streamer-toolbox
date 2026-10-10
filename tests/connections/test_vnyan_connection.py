import asyncio
import json
import unittest

import httpx

from streamer_toolbox.connections.vnyan_connection import VNyanConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from tests.fakes.fake_text_socket_server import FakeTextSocketServer


class TestVNyanConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.posted: list[dict] = []
        self.api_status = 200

        def api(request: httpx.Request) -> httpx.Response:
            self.posted.append({"url": str(request.url), "body": json.loads(request.content)})
            return httpx.Response(self.api_status)

        self.transport = httpx.MockTransport(api)

    def _actions(self, url: str, enabled: bool = True) -> tuple[VNyanConnection, ActionRegistry]:
        connection = VNyanConnection({"enabled": enabled, "url": url}, transport=self.transport)
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    def test_it_is_off_until_switched_on(self) -> None:
        connection = VNyanConnection({})
        self.assertFalse(connection.settings["enabled"])
        self.assertEqual(connection.settings["url"], "ws://localhost:8000/vnyan")

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

    async def test_an_api_message_is_posted_with_every_value_as_text(self) -> None:
        connection, actions = self._actions("ws://127.0.0.1:1/vnyan")
        await actions.run("vnyan.api_message", action="hat", values='{"color": "red", "size": 2, "on": true}')
        await actions.run("vnyan.api_message", action="hat", values={"list": [1, 2]})
        await actions.run("vnyan.api_message", action="plain")
        self.assertEqual([p["body"] for p in self.posted], [
            {"action": "hat", "payload": {"color": "red", "size": "2", "on": "true"}},
            {"action": "hat", "payload": {"list": "[1, 2]"}},
            {"action": "plain", "payload": {}}])
        self.assertTrue(self.posted[0]["url"].startswith("http://localhost:8069"))
        with self.assertRaises(ValueError):
            await actions.run("vnyan.api_message", action="hat", values="red")
        self.api_status = 500
        with self.assertRaises(RuntimeError):
            await actions.run("vnyan.api_message", action="hat")

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
            await off.run("vnyan.api_message", action="hat")
        self.assertEqual(self.posted, [])

    async def test_it_is_green_again_after_a_message_got_through(self) -> None:
        async with FakeTextSocketServer("/vnyan") as server:
            connection, actions = self._actions(server.url)
            self.assertEqual(connection.status.state, ConnectionState.OFF)
            await actions.run("vnyan.send", message="confetti")
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)

    @staticmethod
    async def _until(check, tries: int = 150) -> None:
        for _ in range(tries):
            if check():
                return
            await asyncio.sleep(0.02)
        raise AssertionError("timed out")


if __name__ == "__main__":
    unittest.main()
