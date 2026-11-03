import unittest

from streamer_toolbox.core.event_types.event_type import EventType, check_event_name
from streamer_toolbox.core.event_types.event_value import EventValue, check_value_name, names_in


class TestEventType(unittest.TestCase):
    def test_it_comes_back_as_it_was_saved(self) -> None:
        kind = EventType("follow", (EventValue("user", "Kit", "text", ("name",)), EventValue("color", "", "colour")),
                         ("follower-latest",), default=True, hidden=True)
        self.assertEqual(EventType.from_dict(kind.to_dict()), kind)

    def test_an_unknown_value_kind_is_text(self) -> None:
        self.assertEqual(EventValue.from_dict({"name": "x", "kind": "laser"}).kind, "text")

    def test_names(self) -> None:
        self.assertEqual(check_event_name(" follower-latest "), "follower-latest")
        self.assertEqual(check_value_name("displayName"), "displayName")
        for wrong in ("", "two words", "1st"):
            with self.assertRaises(ValueError):
                check_event_name(wrong)
        with self.assertRaises(ValueError):
            check_value_name("display-name")
        self.assertEqual(names_in("follower-latest, name  name"), ("follower-latest", "name"))

    def test_a_value_keeps_its_kind_and_falls_back_to_its_default(self) -> None:
        self.assertEqual(EventValue("bits", "100", "number").value(""), 100)
        self.assertEqual(EventValue("bits", "", "number").value("2.5"), 2.5)
        self.assertEqual(EventValue("bits", "", "number").value("lots"), "lots")
        self.assertIs(EventValue("gift", "false", "yes_no").value(None), False)
        self.assertEqual(EventValue("code").value("007"), "007")  # rule 25: text stays text
        self.assertEqual(EventType("raid", (EventValue("viewers", "1", "number"),)).filled({}), {"viewers": 1})

    def test_known_as_its_own_name_and_its_other_names(self) -> None:
        kind = EventType("follow", also_known_as=("follower-latest",))
        self.assertTrue(kind.known_as("follow") and kind.known_as("follower-latest"))
        self.assertFalse(kind.known_as("sub"))


if __name__ == "__main__":
    unittest.main()
