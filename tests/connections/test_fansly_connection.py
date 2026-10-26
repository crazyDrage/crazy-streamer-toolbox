import asyncio
import json
import time
import unittest

from streamer_toolbox.connections.fansly_connection import FanslyConnection, chatroom_id
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

ROOM = "100000000000000001"


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestFanslyConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    async def test_it_joins_the_chatroom_keeps_the_line_alive_and_tells_chat_messages(self) -> None:
        async with FakeJsonSocketServer() as server:
            connection = FanslyConnection({"enabled": True, "chatroom": f"https://fansly.com/chatroom/{ROOM}"},
                                          self.events, server.url + "/?v=3", retry_delay=0.05, beat=(0.05, "p"))
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(server.paths, ["/?v=3"])
            await until(lambda: len(server.received) >= 3)
            self.assertEqual(server.received[0], {"t": 46001, "d": json.dumps({"chatRoomId": ROOM})})
            self.assertEqual(server.received[1:3], ["p", "p"])
            message = {"type": 10, "chatRoomMessage": {"content": "hello", "metadata": "{}", "username": "FoxFan"}}
            await server.tell({"t": 10000, "d": json.dumps({"serviceId": 46, "event": json.dumps(message)})})
            await until(lambda: any(kind == "fansly.chat" for kind, _ in self.seen))
            chat = next(data for kind, data in self.seen if kind == "fansly.chat")
            self.assertEqual((chat["user"], chat["message"]), ("FoxFan", "hello"))
            await connection.stop()

    async def test_the_chatroom_is_needed(self) -> None:
        connection = FanslyConnection({"enabled": True}, self.events, "ws://127.0.0.1:1/")
        self.assertIn("No chatroom yet", (await connection.test(connection.settings)).detail)
        self.assertFalse(FanslyConnection({}, self.events).settings["enabled"])

    def test_the_chatroom_id_comes_from_the_number_or_the_whole_address(self) -> None:
        self.assertEqual(chatroom_id({"chatroom": f" {ROOM} "}), ROOM)
        self.assertEqual(chatroom_id({"chatroom": f"https://fansly.com/chatroom/{ROOM}/"}), ROOM)
        for wrong in ("", "https://fansly.com/chatroom/", "abc"):
            with self.assertRaises(ValueError):
                chatroom_id({"chatroom": wrong})


if __name__ == "__main__":
    unittest.main()
