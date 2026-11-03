import unittest

from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.gui.components.flow_editor.trigger_catalog import TriggerCatalog, group_of
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_INFO, TRIGGER_KINDS


class TestTriggerCatalog(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = TriggerCatalog(TRIGGER_KINDS)

    def test_a_trigger_is_listed_under_the_program_that_tells_it(self) -> None:
        self.assertEqual([group_of(k) for k in ("timer", "tip")], ["Toolbox"] * 2)
        self.assertEqual([group_of(k) for k in ("chat", "follow", "offline")], ["Any platform"] * 3)
        self.assertEqual([group_of(k) for k in ("twitch.chat", "vts.hotkey", "key.pressed", "heartrate",
                                                "youtube.member", "tits.hit", "my_lamp.blinked")],
                         ["Twitch", "VTube Studio", "Keyboard", "Heart rate", "YouTube", "T.I.T.S.", "My lamp"])

    def test_the_toolbox_and_any_platform_come_first_then_the_programs_by_name(self) -> None:
        groups = [group for group, _ in self.catalog.groups()]
        self.assertEqual(groups[:2], ["Toolbox", "Any platform"])
        self.assertEqual(groups[2:], sorted(groups[2:], key=str.casefold))
        self.assertEqual(sum(count for _, count in self.catalog.groups()), len(TRIGGER_KINDS))

    def test_a_group_lists_its_triggers_by_title_with_info_and_fields(self) -> None:
        twitch = self.catalog.entries("Twitch")
        self.assertEqual([e.title for e in twitch], sorted((e.title for e in twitch), key=str.casefold))
        redeem = next(e for e in twitch if e.kind == "twitch.redeem")
        self.assertEqual((redeem.match, redeem.example, redeem.fields),
                         ("reward", "", EVENT_FIELDS["twitch.redeem"]))
        self.assertIn("reward", redeem.info)

    def test_a_streamsocket_event_is_matched_by_its_id(self) -> None:
        event = next(e for e in self.catalog.entries("StreamSocket") if e.kind == "streamsocket.event")
        self.assertEqual((event.match, event.example), ("event_id", "*"))

    def test_search_looks_in_titles_info_and_fields_of_every_group(self) -> None:
        found = dict(self.catalog.search("chat message"))
        self.assertEqual(found["Twitch"][0].kind, "twitch.chat")  # the title that starts with the search
        self.assertIn("Any platform", found)
        self.assertEqual([e.kind for _, items in self.catalog.search("hotkey_id") for e in items], ["vts.hotkey"])
        self.assertEqual(self.catalog.search("no such thing"), [])
        self.assertEqual(self.catalog.search("  "), [])

    def test_every_built_in_trigger_has_its_line_of_info_and_its_fields(self) -> None:
        self.assertEqual(set(TRIGGER_KINDS) - set(TRIGGER_INFO), set())
        self.assertEqual(set(TRIGGER_KINDS) - set(EVENT_FIELDS), set())


if __name__ == "__main__":
    unittest.main()
