import unittest
from dataclasses import replace

from streamer_toolbox.core.event_types.default_event_types import DEFAULTS
from streamer_toolbox.core.event_types.event_value import EventValue
from streamer_toolbox.core.widgets.design_values import DesignValues


class DesignValuesTest(unittest.TestCase):
    def test_codes_read_as_names_and_back(self) -> None:
        code = "Latest: {session.twitch.follower-latest.name} ({event.data.amount}) {session.twitch.odd-thing.x}"
        words = DesignValues.to_words(code)
        self.assertEqual("Latest: [Latest follower] ([Amount (months, bits, viewers)]) "
                         "{session.twitch.odd-thing.x}", words)
        self.assertEqual(code, DesignValues.to_codes(words))
        self.assertEqual("{session.twitch.follower-latest.name} [no such]",
                         DesignValues.to_codes("[latest FOLLOWER] [no such]"))

    def test_an_alert_has_the_event_values_too(self) -> None:
        self.assertNotIn("Their name", dict(DesignValues.names(False)))
        self.assertEqual("{event.data.username}", dict(DesignValues.names(True))["Their name"])

    def test_an_event_lists_entry_has_its_event_types_values_by_their_names(self) -> None:
        # his 11-13: "the values should be 1to1 the same name as the event values"
        names = [value["name"] for value in DesignValues.list_values("message", list(DEFAULTS))]
        self.assertEqual(["user", "message", "color", "role", "platform", "user_id", "message_id", "picture",
                          "emoji_dict"], names)
        cheer = {value["name"]: value for value in DesignValues.list_values("cheer", list(DEFAULTS))}
        self.assertEqual(["user", "bits", "message", "platform"], list(cheer))
        self.assertEqual((["amount"], "100"), (cheer["bits"]["aka"], cheer["bits"]["default"]))

    def test_a_sub_has_the_values_of_sub_resub_and_gift_once_each(self) -> None:
        sub = {value["name"]: value for value in DesignValues.list_values("subscriber", list(DEFAULTS))}
        self.assertEqual(["user", "tier", "gift", "platform", "months", "message", "amount"], list(sub))
        self.assertEqual(["name", "sender"], sub["user"]["aka"])

    def test_a_value_he_added_on_the_events_page_is_there_too(self) -> None:
        raid = next(kind for kind in DEFAULTS if kind.name == "raid")
        mine = replace(raid, values=(*raid.values, EventValue("team")))
        self.assertIn("team", [value["name"] for value in DesignValues.list_values("raid", [mine])])

    def test_the_example_is_each_values_default(self) -> None:
        sample = DesignValues.list_sample(DesignValues.list_values("raid", list(DEFAULTS)))
        self.assertEqual({"user": "TestViewer", "viewers": "1", "platform": "twitch"}, sample)

    def test_filled_from_the_session_or_an_example(self) -> None:
        session = {"follower-latest": {"name": "fox"}, "subscriber-latest": {"name": ""},
                   "follower-session": {"count": 4}}
        self.assertEqual([("Hi ", False), ("fox", True), (", ", False), ("TestViewer", True), (" ", False),
                          ("4", True), ("TestViewer", True)],
                         DesignValues.fill("Hi {session.twitch.follower-latest.name}, "
                                           "{session.twitch.subscriber-latest.name} "
                                           "{session.twitch.follower-session.count}{event.data.username}", session))

    def test_a_ticker_names_the_recent_ones(self) -> None:
        ticker = {"kind": "tip", "count": 2, "amount": True, "between": " | ", "look": "still"}
        session = {"tip-recent": [{"name": "a", "amount": 5}, {"name": "b", "amount": 0}, {"name": "c"}]}
        self.assertEqual([("a ($5)", True), (" | ", False), ("b", True)], DesignValues.ticker(ticker, session))
        self.assertEqual([("TestViewer", True), ("\n", False), ("TestViewer 2", True)],
                         DesignValues.ticker({**ticker, "kind": "raid", "amount": False, "look": "lines"}, {}))


if __name__ == "__main__":
    unittest.main()
