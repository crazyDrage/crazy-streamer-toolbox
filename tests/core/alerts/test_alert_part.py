import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_part import AlertPart
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.alerts.alert_store import AlertStore

RESUB = {"user": "Kit", "tier": 1, "months": 7, "message": "still here"}


class TestAlertPart(unittest.TestCase):
    def setUp(self) -> None:
        self.rule = AlertRule.default("twitch.resub")

    def _said(self, rule: AlertRule, data: dict = RESUB) -> list[tuple[str, str]]:
        return [(view["kind"], view["text"]) for view in rule.alert_for(data).parts]

    def test_an_alert_starts_with_the_text_line_and_their_message(self) -> None:
        self.assertEqual(self.rule.parts, (AlertPart("text"), AlertPart("message")))
        self.assertEqual(self._said(self.rule), [("text", "Kit subscribed for 7 months!"), ("message", "still here")])
        self.assertEqual(self._said(self.rule, {**RESUB, "message": ""}),
                         [("text", "Kit subscribed for 7 months!")])  # nothing written: no empty piece
        self.assertEqual(AlertRule.default("twitch.follow").parts, (AlertPart("text"),))  # a follow has no message

    def test_pieces_are_added_taken_away_and_moved_up(self) -> None:
        rule = self.rule.add_part(AlertPart("name")).add_part(AlertPart("amount", text="{amount} months old"))
        self.assertEqual([kind for kind, _ in self._said(rule)], ["text", "message", "name", "amount"])
        rule = rule.without_part(0).part_up(2)
        self.assertEqual(self._said(rule), [("message", "still here"), ("amount", "7 months old"), ("name", "Kit")])
        self.assertEqual(rule.part_up(0), rule)  # the first one stays
        self.assertEqual(self._said(replace(rule, parts=())), [])  # an empty list shows no words

    def test_a_card_gets_each_piece_in_its_box(self) -> None:
        """His sub card: a name box, "Age: __ Months old", a message box; no text line."""
        rule = replace(self.rule, parts=(
            AlertPart("name", on_picture=True, x=33, y=53, align="left"),
            AlertPart("amount", on_picture=True, x=41, y=63),
            AlertPart("message", on_picture=True, x=33, y=81, width=60, align="left", size=30)))
        views = rule.alert_for(RESUB).parts
        self.assertEqual([(v["kind"], v["index"], v["text"]) for v in views],
                         [("name", 0, "Kit"), ("amount", 1, "7"), ("message", 2, "still here")])
        self.assertEqual((views[0]["x"], views[0]["align"], views[2]["width"], views[2]["size"]),
                         (33, "left", 60, 30))
        alert = rule.alert_for(RESUB)
        self.assertEqual((alert.text, alert.message), ("", "still here"))

    def test_a_kind_can_be_there_more_than_once(self) -> None:
        rule = self.rule.add_part(AlertPart("text", text="Welcome back, {user}", on_picture=True))
        self.assertEqual(self._said(rule), [("text", "Kit subscribed for 7 months!"), ("message", "still here"),
                                            ("text", "Welcome back, Kit")])
        self.assertEqual(rule.alert_for(RESUB).text, "Kit subscribed for 7 months!")  # the first text line
        follow = AlertRule.default("twitch.follow").add_part(AlertPart("amount"))
        self.assertEqual(self._said(follow, {"user": "Kit"}), [("text", "Kit just followed!")])  # no amount

    def test_a_dragged_piece_keeps_its_place_in_the_list(self) -> None:
        rule = self.rule.add_part(AlertPart("name", on_picture=True))
        rule = rule.with_part(2, replace(rule.parts[2], x=30, y=20))
        self.assertEqual(rule.parts, (AlertPart("text"), AlertPart("message"),
                                      AlertPart("name", on_picture=True, x=30, y=20)))

    def test_the_message_isnt_said_twice_in_the_stack(self) -> None:
        rule = replace(self.rule, text="{user}: {message}")
        self.assertEqual([kind for kind, _ in self._said(rule)], ["text"])
        on_card = rule.with_part(1, AlertPart("message", on_picture=True))
        self.assertEqual([kind for kind, _ in self._said(on_card)], ["text", "message"])  # its own box

    def test_the_list_is_kept_as_it_is(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "alerts.json"
            parts = (AlertPart("name", on_picture=True, x=10, y=20), AlertPart("text"), AlertPart("name"))
            AlertStore(path).save(replace(self.rule, parts=parts))
            self.assertEqual(AlertStore(path).get("twitch.resub").parts, parts)
            AlertStore(path).save(replace(self.rule, parts=()))
            self.assertEqual(AlertStore(path).get("twitch.resub").parts, ())  # emptied stays empty

    def test_files_where_each_kind_had_a_shown_switch(self) -> None:
        """Before the list: one entry per kind; a kind that wasn't there had its default (text line and
        message shown)."""
        old = {"parts": [{"key": "amount", "shown": True, "on_picture": True, "x": 41, "y": 63},
                         {"key": "text", "shown": False},
                         {"key": "name", "shown": True, "text": "{user}", "size": 28}]}
        rule = AlertRule.from_dict("twitch.resub", old)
        self.assertEqual(rule.parts, (AlertPart("name", text="{user}", size=28),
                                      AlertPart("amount", on_picture=True, x=41, y=63), AlertPart("message")))
        self.assertEqual(AlertRule.from_dict("twitch.resub", {"parts": []}).parts, self.rule.parts)
        follow = AlertRule.from_dict("twitch.follow", {"parts": [{"key": "amount", "shown": True}]})
        self.assertEqual(follow.parts, (AlertPart("text"),))  # a follow has no amount and no message
        self.assertNotIn("parts", rule.to_dict())
        self.assertEqual(AlertRule.from_dict("twitch.resub", rule.to_dict()), rule)

    def test_files_from_before_there_were_pieces(self) -> None:
        old = {"on": True, "text": "{user} is back", "with_message": False,
               "look": {"text_place": "over", "text_x": 20.5, "text_y": 80, "animation_in": "pop"}}
        rule = AlertRule.from_dict("twitch.resub", old)
        self.assertEqual(rule.parts, (AlertPart("text", on_picture=True, x=20.5, y=80.0),))
        self.assertEqual((rule.look.text_place, rule.look.animation_in), ("below", "pop"))
        json.dumps(rule.to_dict())  # and it can be written again

    def test_wrong_values_in_a_piece_fall_back(self) -> None:
        part = AlertPart.from_dict({"kind": "name", "x": 300, "y": "top", "width": -5, "align": "justify"})
        self.assertEqual((part.x, part.y, part.width, part.align), (100.0, 0.0, 0.0, "center"))
        rule = AlertRule.from_dict("twitch.resub", {"pieces": [{"kind": "name"}, {"kind": "nope"}, "name"]})
        self.assertEqual(rule.parts, (AlertPart("name"),))

    def test_the_overlay_gets_the_pieces_and_the_box_still_works(self) -> None:
        queue = AlertQueue()
        rule = self.rule.with_part(1, AlertPart("name", on_picture=True, x=33, y=53))
        payload = queue.payload(rule.alert_for(RESUB))
        self.assertEqual([p["kind"] for p in payload["parts"]], ["text", "name"])
        self.assertEqual(payload["parts"][1], {"kind": "name", "index": 1, "text": "Kit", "on_picture": True,
                                               "x": 33, "y": 53, "width": 0.0, "size": 0.0, "color": "",
                                               "align": "center"})
        plain = queue.payload(Alert("hi", message="there"))  # the Show alert box: a text and a message
        self.assertEqual(plain["parts"], [{"kind": "text", "text": "hi"}, {"kind": "message", "text": "there"}])


if __name__ == "__main__":
    unittest.main()
