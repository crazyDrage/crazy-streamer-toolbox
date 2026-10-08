import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.connections.lumia_connection import LumiaConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

TOKEN = "lumia-secret-token"
# the shape of Lumia's documented settings answer, shortened
SETTINGS = {"data": {"premium": True, "types": ["alert", "chat-command", "hex-color", "tts", "studio-scene"],
                     "options": {"chat-command": {"values": ["red", "blue"]},
                                 "alert": {"values": {"twitch": ["twitch-follower", "twitch-bits"],
                                                      "youtube": ["youtube-member"]}}},
                     "lights": [{"id": "1", "name": "Desk", "type": "hue"}]}}


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestLumiaConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.token = Path(self._dir.name) / "lumia_token.txt"
        self.token.write_text(TOKEN + "\n", encoding="utf-8")
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []
        self.sent: list[dict] = []
        self.refuse = False

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _lumia(self, request: httpx.Request) -> httpx.Response:
        if request.url.params.get("token") != TOKEN:
            return httpx.Response(401, json={"status": 401, "error": "invalid token"})
        if request.url.path == "/api/retrieve":
            return httpx.Response(200, json=SETTINGS)
        body = json.loads(request.content)
        if self.refuse:
            return httpx.Response(400, json={"status": 400, "error": "type is invalid"})
        self.sent.append(body)
        return httpx.Response(200, json={"status": 200})

    def _connection(self, url: str = "http://localhost:39231", enabled: bool = True
                    ) -> tuple[LumiaConnection, ActionRegistry]:
        connection = LumiaConnection({"enabled": enabled, "url": url}, self.token, self.events,
                                     retry_delay=0.05, transport=httpx.MockTransport(self._lumia))
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    async def test_commands_alerts_and_colours_go_through_the_send_api(self) -> None:
        connection, actions = self._connection()
        tried = await connection.test(connection.settings)
        self.assertEqual((tried.state, tried.facts), (ConnectionState.CONNECTED, (("Lights", "1"),)))
        self.assertEqual(await actions.get("lumia.command").options["command"](), ["blue", "red"])
        self.assertEqual(await actions.get("lumia.alert").options["alert"](),
                         ["twitch-bits", "twitch-follower", "youtube-member"])
        self.assertIn("tts", await actions.get("lumia.send").options["kind"]())
        await actions.run("lumia.command", command="blue", hold=True)
        await actions.run("lumia.alert", alert="twitch-bits", values='{"username": "ann", "bits": 100}')
        await actions.run("lumia.color", color="#00FF00", brightness=150, seconds=2, fade=0.5)
        await actions.run("lumia.send", kind="studio-scene", value="Party")
        self.assertEqual(self.sent, [
            {"type": "chat-command", "params": {"value": "blue", "hold": True}},
            {"type": "alert", "params": {"value": "twitch-bits", "extraSettings": {"username": "ann", "bits": 100}}},
            {"type": "hex-color", "params": {"value": "#00FF00", "brightness": 100.0, "transition": 500,
                                             "duration": 2000}},
            {"type": "studio-scene", "params": {"value": "Party"}}])
        with self.assertRaises(ValueError):
            await actions.run("lumia.color", color="green")
        self.refuse = True
        with self.assertRaisesRegex(RuntimeError, "type is invalid"):
            await actions.run("lumia.send", kind="nonsense")

    async def test_the_token_is_needed_and_never_shown(self) -> None:
        self.token.write_text("", encoding="utf-8")
        connection, actions = self._connection()
        self.assertIn("No token yet", (await connection.test(connection.settings)).detail)
        with self.assertRaisesRegex(NotConnectedError, "No token yet"):
            await actions.run("lumia.command", command="blue")
        self.token.write_text("another-token", encoding="utf-8")
        tried = await connection.test(connection.settings)
        self.assertEqual(tried.detail, "Lumia Stream: invalid token")
        _, off = self._connection(enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("lumia.command", command="blue")

        def down(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError(f"refused {request.url}")

        gone = LumiaConnection({"enabled": True}, self.token, self.events, transport=httpx.MockTransport(down))
        detail = (await gone.test(gone.settings)).detail
        self.assertIn("can't reach Lumia Stream", detail)
        self.assertNotIn("another-token", detail)

    async def test_what_lumia_sees_starts_flows(self) -> None:
        async with FakeJsonSocketServer() as server:
            connection, _ = self._connection(server.url.replace("ws://", "http://"))
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(server.paths, [f"/api?token={TOKEN}"])
            await server.tell({"event": "socketapi:response", "context": 1, "status": 200, "type": "x"})
            await server.tell({"origin": "twitch", "type": "alert", "event": "twitch-follower",
                               "data": {"username": "ann", "extraSettings": {"time": "10:00:00"}}})
            await server.tell({"origin": "twitch", "type": "chat", "data": {"username": "bob", "message": "hi"}})
            await until(lambda: len(self.seen) == 2)
            self.assertEqual([(d["type"], d["alert"], d["user"], d["message"]) for _, d in self.seen],
                             [("alert", "twitch-follower", "ann", ""), ("chat", "", "bob", "hi")])
            self.assertEqual(set(self.seen[0][1]), set(EVENT_FIELDS["lumia.event"]))
            await connection.stop()
        self.token.write_text("", encoding="utf-8")
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("No token yet", connection.status.detail)
        await connection.stop()


if __name__ == "__main__":
    unittest.main()
