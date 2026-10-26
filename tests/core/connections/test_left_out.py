import unittest

from streamer_toolbox.core.connections.left_out import gone, owners
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_KINDS, offered_triggers


class TestLeftOut(unittest.TestCase):
    def test_an_event_belongs_to_the_connection_it_is_named_after_or_to_the_ones_listed(self) -> None:
        self.assertEqual(owners("rumble.follow"), ("rumble",))
        self.assertEqual(owners("heartrate"), ("pulsoid", "hyperate"))
        self.assertEqual(owners("key.pressed"), ("keyboard",))
        self.assertEqual(owners("timer"), ("timer",))

    def test_an_event_is_gone_only_when_everything_that_publishes_it_is_missing(self) -> None:
        self.assertTrue(gone("rumble.follow", {"rumble", "youtube"}))
        self.assertFalse(gone("twitch.follow", {"rumble"}))
        self.assertFalse(gone("heartrate", {"pulsoid"}))
        self.assertTrue(gone("heartrate", {"pulsoid", "hyperate"}))
        for nobodys in ("timer", "tip", "follow", "chat"):
            self.assertFalse(gone(nobodys, {"twitch", "rumble", "keyboard"}))

    def test_the_flow_editor_offers_no_trigger_of_a_switched_off_connection(self) -> None:
        offered = offered_triggers(lambda: {"vts": "VTube Studio", "rumble": "Rumble", "keyboard": "Keyboard"})
        self.assertNotIn("vts.hotkey", offered)
        self.assertNotIn("rumble.chat", offered)
        self.assertNotIn("key.pressed", offered)
        for kept in ("twitch.redeem", "follow", "timer", "tip"):
            self.assertIn(kept, offered)
        self.assertEqual(offered["timer"], TRIGGER_KINDS["timer"])
        self.assertIn("vts.hotkey", offered_triggers(None))


if __name__ == "__main__":
    unittest.main()
