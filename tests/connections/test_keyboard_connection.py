import asyncio
import unittest

from streamer_toolbox.connections.keyboard_connection import KEY_PRESSED, KeyboardConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from tests.fakes.fake_key_listener import FakeKeyListener


class TestKeyboardConnection(unittest.IsolatedAsyncioTestCase):
    async def test_only_wanted_keys_become_events_and_typing_is_not_shown(self) -> None:
        events, seen = EventBus(), []

        async def handler(kind, data):
            seen.append((kind, data))

        events.subscribe(handler)
        listener = FakeKeyListener()
        keyboard = KeyboardConnection({"enabled": True}, listener, events, wanted=lambda name: name in ("f23", "ctrl+k"))
        await keyboard.start()
        self.assertEqual(keyboard.status.state, ConnectionState.CONNECTED)
        for name in ("f23", "p", "a", "f24", "ctrl+k"):  # from the listener's own thread
            await asyncio.to_thread(listener.press, name)
        await asyncio.sleep(0.05)
        self.assertEqual(seen, [(KEY_PRESSED, {"key": "f23"}), (KEY_PRESSED, {"key": "ctrl+k"})])
        self.assertIn(("Last special key", "ctrl+k"), keyboard.status.facts)
        await asyncio.to_thread(listener.press, "a")  # typing: not an event, not shown
        await asyncio.sleep(0.05)
        self.assertIn(("Last special key", "ctrl+k"), keyboard.status.facts)
        self.assertEqual(len(seen), 2)
        await keyboard.stop()
        self.assertTrue(listener.stopped)

    async def test_a_missing_library_shows_on_the_tab(self) -> None:
        class Broken(FakeKeyListener):
            def start(self, on_key):
                raise ImportError("No module named 'pynput'")

        keyboard = KeyboardConnection({"enabled": True}, Broken(), EventBus(), wanted=lambda name: True)
        await keyboard.start()
        self.assertEqual(keyboard.status.state, ConnectionState.ERROR)
        self.assertIn("pynput", keyboard.status.detail)
