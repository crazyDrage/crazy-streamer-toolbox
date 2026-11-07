import unittest

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
