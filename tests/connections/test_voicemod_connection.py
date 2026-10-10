import asyncio
import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.connections.voicemod_connection import VoicemodConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

KEY = "voicemod-secret-key"


def voicemod(message: dict, path: str) -> dict | None:
    """Answers like Voicemod's API reference; what it doesn't show an answer for gets none."""
    action = message["action"]
    if action == "registerClient":
        code = 200 if message["payload"]["clientKey"] == KEY else 401
        return {"action": action, "id": message["id"], "payload": {"status": {"code": code, "description": "x"}}}
    if action == "getVoices":
        return {"actionType": action, "actionID": message["id"], "actionObject": {"currentVoice": "nofx", "voices": [
            {"id": "cave", "friendlyName": "Cave", "enabled": True},
            {"id": "robot", "friendlyName": "Robot", "enabled": True},
            {"id": "paid", "friendlyName": "Paid one", "enabled": False}]}}
    if action == "getMemes":
        return {"actionType": action, "actionID": message["id"], "actionObject": {"listOfMemes": [
            {"Name": "Airhorn", "FileName": "f-1", "Type": "PlayRestart"}]}}
    if action == "toggleHearMyVoice":
        return {"actionType": action, "actionID": message["id"], "actionObject": {"value": True}}
    return None


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestVoicemodConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.key = Path(self._dir.name) / "voicemod_key.txt"
        self.key.write_text(KEY, encoding="utf-8")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _connection(self, url: str = "", enabled: bool = True, ports: tuple[int, ...] = (1,)
                    ) -> tuple[VoicemodConnection, ActionRegistry]:
        connection = VoicemodConnection({"enabled": enabled, "url": url}, self.key, retry_delay=0.05, ports=ports)
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    async def test_voices_and_sounds_are_picked_by_name(self) -> None:
        async with FakeJsonSocketServer(voicemod) as server:
            connection, actions = self._connection(server.url + "/v1")
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(server.paths, ["/v1"])
            self.assertEqual(await actions.get("voicemod.voice").options["voice"](), ["No effect", "Cave", "Robot"])
            self.assertEqual(await actions.get("voicemod.play_sound").options["sound"](), ["Airhorn"])
            await actions.run("voicemod.voice", voice="robot")
            await actions.run("voicemod.voice", voice="No effect")
            await actions.run("voicemod.play_sound", sound="Airhorn")
            await actions.run("voicemod.random_voice", among="FavoriteVoices")
            await actions.run("voicemod.stop_sounds")
            await until(lambda: server.received[-1]["action"] == "stopAllMemeSounds")
            sent = [(m["action"], m["payload"]) for m in server.received if m["action"] not in
                    ("registerClient", "getVoices", "getMemes")]
            self.assertEqual(sent, [("loadVoice", {"voiceID": "robot"}), ("loadVoice", {"voiceID": "nofx"}),
                                    ("playMeme", {"FileName": "f-1", "IsKeyDown": True}),
                                    ("selectRandomVoice", {"mode": "FavoriteVoices"}), ("stopAllMemeSounds", {})])
            self.assertTrue(all(m.get("id") for m in server.received))  # Voicemod wants one on every message
            self.assertEqual(await actions.run("voicemod.toggle", switch="Hear myself"), {"on": True})
            with self.assertRaisesRegex(KeyError, "no voice named"):
                await actions.run("voicemod.voice", voice="Paid one")
            with self.assertRaises(ValueError):
                await actions.run("voicemod.toggle", switch="Everything")
            await connection.stop()

    async def test_the_key_is_needed_and_a_refused_one_stops_it(self) -> None:
        async with FakeJsonSocketServer(voicemod) as server:
            self.key.write_text("wrong-key", encoding="utf-8")
            connection, _ = self._connection(server.url + "/v1")
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.ERROR)
            self.assertEqual(connection.status.detail, "Voicemod refused the API key")
            self.key.write_text("", encoding="utf-8")
            self.assertIn("No API key yet", (await connection.test(connection.settings)).detail)
            await connection.start()
            await until(lambda: "No API key yet" in connection.status.detail)
            await connection.stop()

    async def test_voicemod_is_looked_for_on_each_of_its_ports(self) -> None:
        async with FakeJsonSocketServer(voicemod) as server:
            port = int(server.url.rsplit(":", 1)[1])
            connection, actions = self._connection(ports=(1, port))
            tried = await connection.test(connection.settings)
            self.assertEqual((tried.state, tried.facts), (ConnectionState.CONNECTED, (("Port", str(port)),)))
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            await connection.stop()
        gone, actions = self._connection()
        self.assertIn("can't find Voicemod", (await gone.test(gone.settings)).detail)
        await gone.start()
        with self.assertRaisesRegex(NotConnectedError, "not connected"):
            await actions.run("voicemod.stop_sounds")
        await gone.stop()
        _, off = self._connection(enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("voicemod.stop_sounds")


if __name__ == "__main__":
    unittest.main()
