import unittest
from dataclasses import replace

from streamer_toolbox.core.alerts.alert_part import AlertPart
from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.alerts.alert_variation import AlertVariation
from streamer_toolbox.gui.components.alerts_tool.alerts_tool import summary


class TestAlertsToolSummary(unittest.TestCase):
    def test_an_alert_in_one_line(self) -> None:
        rule = AlertRule.default("twitch.resub")
        self.assertEqual(summary(rule), "no picture · no sound · 5 s")
        card = replace(rule, image="C:\\alerts\\sub_own_with_name.png", sound="C:\\alerts\\ding.ogg", seconds=8.0,
                       variations=(AlertVariation(12),)) \
            .add_part(AlertPart("name", on_picture=True)) \
            .add_part(AlertPart("amount", on_picture=True))
        self.assertEqual(summary(card), "sub_own_with_name.png · ding.ogg · 8 s · on the picture: name, amount · "
                                        "1 bigger alert")


if __name__ == "__main__":
    unittest.main()
