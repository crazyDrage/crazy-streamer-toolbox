import unittest

from streamer_toolbox.core.widgets.element_design import ElementDesign


class ElementLivePiecesTest(unittest.TestCase):
    """Shapes, goal bars, tickers, and the events a widget needs for what its pieces show."""

    def setUp(self) -> None:
        self.design = ElementDesign.new()

    def test_a_shape_has_a_height(self) -> None:
        name = self.design.add(0, "shape")
        self.assertEqual("Shape", name)
        self.design.resize(0, name, 300, height=90)
        style = self.design.piece(0, name)["style"]
        self.assertEqual(("300px", "90px", "#9146ff"), (style["width"], style["height"], style["backgroundColor"]))

    def test_a_goal_bar(self) -> None:
        name = self.design.add(0, "goal")
        self.assertEqual({"value": "follower-session.count", "target": 10,
                          "label": "Follower goal: {value} / {target}"}, self.design.goal(0, name))
        self.design.set_goal(0, name, value="cheer-session.amount", target=1000.0)
        self.assertEqual(1000, self.design.goal(0, name)["target"])
        with self.assertRaises(ValueError):
            self.design.set_goal(0, name, value="nonsense")
        self.design.set_fill(0, name, "#00ff00")
        self.assertEqual({"backgroundColor": "#00ff00"}, self.design.piece(0, name)["fillStyle"])
        self.assertEqual({"cheer"}, self.design.events())

    def test_a_ticker(self) -> None:
        name = self.design.add(0, "latestTicker")
        self.assertEqual("Ticker", name)
        self.assertEqual("follower", self.design.ticker(0, name)["kind"])
        self.design.set_ticker(0, name, kind="cheer", count=40, amount=True, look="lines", seconds=6)
        ticker = self.design.ticker(0, name)
        self.assertEqual(("cheer", 25, True, "lines", 6), (ticker["kind"], ticker["count"], ticker["amount"],
                                                           ticker["look"], ticker["seconds"]))
        piece = self.design.piece(0, name)
        self.assertEqual("{session.twitch.cheer-latest.name}", self.design.text(0, name))
        self.assertEqual("pre", piece["style"]["whiteSpace"])
        self.assertEqual({"cheer"}, self.design.events())
        with self.assertRaises(ValueError):
            self.design.set_ticker(0, name, look="dance")

    def test_a_streamelements_ticker_is_its_text(self) -> None:
        name = self.design.add(0, "latestTicker")
        del self.design.piece(0, name)["toolbox"]
        self.assertIsNone(self.design.ticker(0, name))

    def test_a_label_needs_its_events(self) -> None:
        name = self.design.add(0, "text")
        self.assertEqual({"follower"}, self.design.events())
        self.design.set_text(0, name, "{session.twitch.subscriber-session.count} subs, "
                                      "{session.twitch.cheer-latest.amount} bits")
        self.assertEqual({"subscriber", "cheer"}, self.design.events())


if __name__ == "__main__":
    unittest.main()
