import unittest
from dataclasses import replace

from streamer_toolbox.core.alerts.alert_input import AlertInput, clean_name
from streamer_toolbox.core.alerts.alert_part import AlertPart
from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.alerts.alert_variation import AlertVariation


class TestAlertInput(unittest.TestCase):
    """His round 65: an alert gets its own inputs (username, amount, text, a picture, a sound)."""

    def setUp(self) -> None:
        self.rule = AlertRule("lizard", "Lizard", (AlertInput("user", example="Kit"),
                                                   AlertInput("times", "number", "3", True),
                                                   AlertInput("gif", "picture")),
                              on=True, text="{user} fed the lizard {times} times", minimum=2,
                              parts=(AlertPart("text"), AlertPart("name", text="{user}!")),
                              variations=(AlertVariation(10, "{user} feeds the lizard {times} times!!"),))

    def test_its_words_use_its_inputs(self) -> None:
        self.assertEqual(self.rule.alert_for({"user": "Ann", "times": "4"}).text, "Ann fed the lizard 4 times")
        self.assertEqual(self.rule.alert_for(self.rule.examples()).text, "Kit fed the lizard 3 times")
        self.assertEqual(self.rule.alert_for({"times": 12}).text, "Someone feeds the lizard 12 times!!")

    def test_the_amount_input_decides_only_from(self) -> None:
        self.assertEqual(self.rule.amount_input, "times")
        self.assertFalse(self.rule.wants({"times": 1}))
        self.assertTrue(self.rule.wants({"times": "2"}))

    def test_only_one_input_is_the_amount(self) -> None:
        both = self.rule.with_inputs((*self.rule.inputs, AlertInput("extra", "number", amount=True)))
        self.assertEqual([i.name for i in both.inputs if i.amount], ["extra"])

    def test_renaming_an_input_changes_its_name_in_the_words(self) -> None:
        rule = self.rule.renamed_input("user", "viewer")
        self.assertEqual([i.name for i in rule.inputs], ["viewer", "times", "gif"])
        self.assertEqual((rule.text, rule.parts[1].text, rule.variations[0].text),
                         ("{viewer} fed the lizard {times} times", "{viewer}!", "{viewer} feeds the lizard {times} times!!"))

    def test_a_picture_input_shows_its_file_when_the_alert_has_none(self) -> None:
        self.assertEqual(self.rule.alert_for({"user": "Ann", "times": 3, "gif": '"C:\\gifs\\lizard.gif"'}).image,
                         "C:\\gifs\\lizard.gif")
        own = replace(self.rule, image="C:\\gifs\\own.gif")
        self.assertEqual(own.alert_for({"gif": "C:\\gifs\\lizard.gif"}).image, "C:\\gifs\\own.gif")
        said = replace(self.rule, image="C:\\gifs\\{gif}.gif")
        self.assertEqual(said.alert_for({"gif": "big"}).image, "C:\\gifs\\big.gif")

    def test_names_fit_into_braces_and_files_keep_them(self) -> None:
        self.assertEqual((clean_name("Their Message"), clean_name("  9 lives"), clean_name("ok_2")),
                         ("their_message", "", "ok_2"))
        self.assertEqual(AlertRule.from_dict(self.rule.to_dict()), self.rule)
        self.assertEqual(AlertInput.from_dict({"name": "Big Gif", "kind": "nope"}), AlertInput("big_gif"))


if __name__ == "__main__":
    unittest.main()
