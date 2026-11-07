import unittest

from streamer_toolbox.core.widgets.design_preset import PRESETS
from streamer_toolbox.core.widgets.element_design import ElementDesign


class DesignPresetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.design = ElementDesign.new()
        self.always = self.design.layers()[0][0]
        self.alert = self.design.add_alert("cheer")

    def _preset(self, title: str):
        return next(p for p in PRESETS if p.title == title)

    def test_every_one_can_be_added_where_it_fits(self) -> None:
        for preset in PRESETS:
            for layer, alert in ((self.always, False), (self.alert, True)):
                if preset.fits(alert):
                    name = preset.add_to(self.design, layer)
                    self.assertEqual(preset.kind, self.design.piece(layer, name)["type"], preset.title)
        self.assertFalse(self._preset("Sound").fits(False))  # a sound plays with an alert
        self.assertFalse(self._preset("Their name").fits(False))

    def test_it_is_set_up_for_its_job_and_named_after_it(self) -> None:
        name = self._preset("Latest follower").add_to(self.design, self.always)
        self.assertEqual("Latest follower", name)
        self.assertEqual("Latest follower: {session.twitch.follower-latest.name}", self.design.text(self.always, name))
        self.assertEqual("Latest follower 2", self._preset("Latest follower").add_to(self.design, self.always))
        goal = self._preset("Sub goal").add_to(self.design, self.always)
        self.assertEqual("subscriber-session.count", self.design.goal(self.always, goal)["value"])
        ticker = self._preset("Recent cheers").add_to(self.design, self.always)
        self.assertEqual("cheer", self.design.ticker(self.always, ticker)["kind"])
        circle = self.design.piece(self.always, self._preset("Circle").add_to(self.design, self.always))["style"]
        self.assertEqual(("200px", "200px", "50%"), (circle["width"], circle["height"], circle["borderRadius"]))
        self.assertEqual({"follower", "subscriber", "cheer"}, self.design.events())


if __name__ == "__main__":
    unittest.main()
