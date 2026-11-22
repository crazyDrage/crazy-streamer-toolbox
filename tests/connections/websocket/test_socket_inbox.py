import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from streamer_toolbox.connections.websocket.socket_inbox import SocketInbox
from streamer_toolbox.core.connections.inbox_types import InboxTypes
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.events.event_bus import EventBus


class TestSocketInbox(unittest.IsolatedAsyncioTestCase):
    """Messages from a program that connects in (Warudo's "Send Websocket" plugin here) become the event
    <connection id>.message."""

    async def asyncSetUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.key_file = SecretFile(Path(self._dir.name) / "secrets" / "warudo_in_key.txt", "key")
        self.events = EventBus()
        self.heard: list[tuple[str, dict[str, Any]]] = []

        async def hear(kind: str, data: dict[str, Any]) -> None:
            self.heard.append((kind, data))

        self.events.subscribe(hear)
        self.on = True
        self.types = InboxTypes(Path(self._dir.name) / "inbox_types.json")
        self.inbox = SocketInbox("warudo", "Warudo", self.key_file, self.events, lambda: self.on, self.types)

    async def asyncTearDown(self) -> None:
        self._dir.cleanup()

    async def test_the_key_is_made_once_kept_and_can_be_renewed(self) -> None:
        key = self.inbox.key()
        self.assertGreater(len(key), 20)
        self.assertEqual(key, self.inbox.key())
        self.assertEqual(key, self.key_file.read())
        self.assertEqual("", self.inbox.refusal(key))
        new = self.inbox.new_key()
        self.assertNotEqual(key, new)
        self.assertIn("wrong key", self.inbox.refusal(key))

    async def test_nothing_is_let_in_without_a_key_or_while_switched_off(self) -> None:
        self.assertIn("wrong key", self.inbox.refusal(""))  # no key made yet
        key = self.inbox.key()
        self.on = False
        self.assertIn("switched off", self.inbox.refusal(key))
        self.assertIn("Connections → Warudo", self.inbox.refusal(key))

    async def test_a_message_becomes_the_event_exactly_as_it_came(self) -> None:
        sent = json.dumps(json.dumps({"name": "Camera 1"}))  # packed twice: his node's JSON Stringify Output (11-21)
        self.inbox.received("camera", sent)
        self.inbox.received("wave", "42")
        await self.events.wait_idle()
        self.assertEqual(self.heard, [  # nothing read into it (his 11-22): JSON text to value does that
            ("warudo.message", {"type": "camera", "text": sent}),
            ("warudo.message", {"type": "wave", "text": "42"})])

    async def test_live_types_count_each_line(self) -> None:
        self.inbox.opened("camera")
        self.inbox.opened("camera")
        self.inbox.opened("wave")
        self.inbox.closed("camera")
        self.assertEqual(["camera", "wave"], self.inbox.live_types())
        self.inbox.closed("camera")
        self.inbox.closed("wave")
        self.assertEqual([], self.inbox.live_types())

    async def test_a_type_is_known_once_it_connected_until_it_is_removed(self) -> None:
        self.assertEqual([], self.inbox.known_types())
        self.inbox.opened("wave")
        self.inbox.opened("Camera")
        self.inbox.closed("wave")
        self.assertEqual(["Camera", "wave"], self.inbox.known_types())
        again = SocketInbox("warudo", "Warudo", self.key_file, self.events, lambda: True, self.types)  # after a restart
        self.assertEqual(["Camera", "wave"], again.known_types())
        self.inbox.forget("wave")
        self.assertEqual(["Camera"], self.inbox.known_types())
        self.inbox.opened("wave")
        self.assertEqual(["Camera", "wave"], self.inbox.known_types())
        self.inbox.add_type("throw")  # his 11-22: listed before it ever connected (the tab's Add)
        self.inbox.add_type("throw")
        self.assertEqual(["Camera", "throw", "wave"], self.inbox.known_types())
        self.assertNotIn("throw", self.inbox.live_types())  # added, not connected


if __name__ == "__main__":
    unittest.main()
