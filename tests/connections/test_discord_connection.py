import json
import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.connections.discord_connection import DiscordConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError

WEBHOOK = "https://discord.com/api/webhooks/123/secret-webhook-token"


class TestDiscordConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.webhook = Path(self._dir.name) / "discord_webhook.txt"
        self.webhook.write_text(WEBHOOK + "\n", encoding="utf-8")
        self.posted: list[dict] = []
        self.asked: list[str] = []
        self.status = 200

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _discord(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(str(request.url))
        if self.status != 200:
            return httpx.Response(self.status, json={"message": "Cannot send an empty message", "code": 50006})
        if request.method == "GET":
            return httpx.Response(200, json={"id": "123", "name": "Stream news", "channel_id": "9"})
        self.posted.append(json.loads(request.content))
        return httpx.Response(204)

    def _connection(self, enabled: bool = True) -> tuple[DiscordConnection, ActionRegistry]:
        connection = DiscordConnection({"enabled": enabled}, self.webhook, httpx.MockTransport(self._discord))
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    async def test_a_message_is_posted_and_pings_only_when_asked(self) -> None:
        connection, actions = self._connection()
        await connection.start()
        self.assertEqual((connection.status.state, connection.status.facts),
                         (ConnectionState.CONNECTED, (("Webhook", "Stream news"),)))
        await actions.run("discord.post", message=" I'm live @everyone ")
        await actions.run("discord.post", message="live @everyone", name="Toolbox", pings=True)
        self.assertEqual(self.posted, [
            {"content": "I'm live @everyone", "allowed_mentions": {"parse": []}},
            {"content": "live @everyone", "username": "Toolbox"}])
        with self.assertRaises(ValueError):
            await actions.run("discord.post", message="  ")
        with self.assertRaisesRegex(ValueError, "at most 2000"):
            await actions.run("discord.post", message="x" * 2001)
        self.status = 400
        with self.assertRaisesRegex(RuntimeError, "Discord: Cannot send an empty message"):
            await actions.run("discord.post", message="hi")
        self.status = 404
        with self.assertRaisesRegex(RuntimeError, "doesn't know this webhook"):
            await actions.run("discord.post", message="hi")

    async def test_the_address_is_checked_before_anything_is_sent_and_never_shown(self) -> None:
        for wrong in ("", "http://discord.com/api/webhooks/1/x", "https://example.com/api/webhooks/1/x",
                      "https://discord.com/channels/1/2"):
            self.webhook.write_text(wrong, encoding="utf-8")
            connection, actions = self._connection()
            self.assertEqual((await connection.test({})).state, ConnectionState.ERROR)
            with self.assertRaises(NotConnectedError):
                await actions.run("discord.post", message="hi")
        self.assertEqual(self.asked, [])
        self.webhook.write_text(WEBHOOK, encoding="utf-8")

        def down(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError(f"refused {request.url}")

        gone = DiscordConnection({"enabled": True}, self.webhook, httpx.MockTransport(down))
        detail = (await gone.test({})).detail
        self.assertEqual(detail, "can't reach Discord (ConnectError)")
        _, off = self._connection(enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("discord.post", message="hi")


if __name__ == "__main__":
    unittest.main()
