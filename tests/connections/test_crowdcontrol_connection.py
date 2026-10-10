import asyncio
import time
import unittest

import websockets

from streamer_toolbox.connections.crowdcontrol_connection import CrowdControlConnection, crowd_control_effect
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

# the effect request from Crowd Control's docs, shortened
REQUEST = {"requestID": "r-1", "effect": {"effectID": "freeze", "type": "game", "name": "Can't Move",
                                          "category": ["Movement"], "duration": 15},
           "game": {"gameID": "Minecraft", "name": "Minecraft"},
           "target": {"ccUID": "ccuid-1", "name": "drage", "profile": "twitch"},
           "requester": {"ccUID": "ccuid-2", "name": "ann", "profile": "twitch"}, "timestamp": 1725981424721}


def crowd_control(message: dict, path: str) -> dict | None:
    if message.get("action") != "subscribe":
        return None
    topics = message["data"]["topics"]
    known = [t for t in topics if t == "pub/ccuid-1"]
    return {"domain": "direct", "type": "subscription-result",
            "payload": {"success": known, "failure": [t for t in topics if t not in known]}}


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestCrowdControlConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def _connection(self, url: str, ccuid: str) -> CrowdControlConnection:
        return CrowdControlConnection({"enabled": True, "ccuid": ccuid}, self.events, url,
                                      connect=websockets.connect, retry_delay=0.05)

    def test_an_effect_becomes_the_toolbox_event(self) -> None:
        event = crowd_control_effect("requested", REQUEST)
        self.assertEqual(event, {"status": "requested", "effect": "Can't Move", "effect_id": "freeze",
                                 "game": "Minecraft", "user": "ann", "target": "drage", "seconds": 15,
                                 "request_id": "r-1"})
        self.assertEqual(set(event), set(EVENT_FIELDS["crowdcontrol.effect"]))
        self.assertEqual(crowd_control_effect("failed", {})["effect"], "")

    async def test_it_listens_to_the_streamers_public_topic(self) -> None:
        async with FakeJsonSocketServer(crowd_control) as server:
            connection = self._connection(server.url, " 1 ")  # typed without the ccuid- in front
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            await until(lambda: len(server.received) == 1)
            self.assertEqual(server.received[0], {"action": "subscribe", "data": {"topics": ["pub/ccuid-1"]}})
            await server.tell({"domain": "pub", "type": "effect-request", "payload": REQUEST, "timestamp": 1})
            await server.tell({"domain": "pub", "type": "effect-success", "payload": REQUEST, "timestamp": 2})
            await server.tell({"domain": "pub", "type": "something-else", "payload": {}, "timestamp": 3})
            await server.tell({"domain": "pub", "type": "effect-failure", "payload": REQUEST, "timestamp": 4})
            await until(lambda: len(self.seen) == 3)
            self.assertEqual([(kind, data["status"], data["user"]) for kind, data in self.seen], [
                ("crowdcontrol.effect", "requested", "ann"), ("crowdcontrol.effect", "succeeded", "ann"),
                ("crowdcontrol.effect", "failed", "ann")])
            await connection.stop()

    async def test_a_missing_or_unknown_id_is_said_plainly(self) -> None:
        async with FakeJsonSocketServer(crowd_control) as server:
            missing = self._connection(server.url, "")
            self.assertIn("No Crowd Control id yet", (await missing.test(missing.settings)).detail)
            unknown = self._connection(server.url, "ccuid-9")
            await unknown.start()
            await until(lambda: "doesn't know this id" in unknown.status.detail)
            await unknown.stop()
        self.assertFalse(CrowdControlConnection({}, self.events).settings["enabled"])


if __name__ == "__main__":
    unittest.main()
