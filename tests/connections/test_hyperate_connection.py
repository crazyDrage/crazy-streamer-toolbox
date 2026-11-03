import asyncio
import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.hyperate_connection import HypeRateConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

KEY = "hyperate-secret-key"
BEAT = {"topic": "phoenix", "event": "heartbeat", "payload": {}, "ref": 0}


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestHypeRateConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.key = Path(self._dir.name) / "hyperate_key.txt"
        self.key.write_text(KEY, encoding="utf-8")
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)
        self.heart = HeartRate(self.events)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_it_joins_its_ids_channel_keeps_the_line_alive_and_tells_the_heart_rate(self) -> None:
        async with FakeJsonSocketServer() as server:
            connection = HypeRateConnection({"enabled": True, "hyperate_id": " AB12 "}, self.key, self.heart,
                                            server.url + "/socket/websocket?token=", retry_delay=0.05,
                                            beat=(0.05, BEAT))
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(server.paths, [f"/socket/websocket?token={KEY}"])
            await until(lambda: len(server.received) >= 3)
            self.assertEqual(server.received[0], {"topic": "hr:AB12", "event": "phx_join", "payload": {}, "ref": 0})
            self.assertEqual(server.received[1:3], [BEAT, BEAT])
            await server.tell({"event": "phx_reply", "payload": {"status": "ok"}, "ref": 0, "topic": "hr:AB12"})
            await server.tell({"event": "hr_update", "payload": {"hr": 99}, "ref": None, "topic": "hr:other"})
            await server.tell({"event": "hr_update", "payload": {"hr": 79}, "ref": None, "topic": "hr:AB12"})
            await until(lambda: len(self.seen) == 1)
            self.assertEqual(self.seen, [("heartrate", {"bpm": 79, "previous_bpm": 0, "source": "hyperate"})])
            await connection.stop()

    async def test_the_id_and_the_key_are_needed(self) -> None:
        connection = HypeRateConnection({"enabled": True}, self.key, self.heart, "ws://127.0.0.1:1/?token=")
        self.assertIn("No HypeRate id yet", (await connection.test(connection.settings)).detail)
        self.key.write_text("", encoding="utf-8")
        connection.configure({"enabled": True, "hyperate_id": "AB12"})
        self.assertIn("No websocket key yet", (await connection.test(connection.settings)).detail)
        self.assertFalse(HypeRateConnection({}, self.key, self.heart).settings["enabled"])


if __name__ == "__main__":
    unittest.main()
