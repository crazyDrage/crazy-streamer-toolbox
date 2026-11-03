import unittest

from streamer_toolbox.core.widgets.widget_events import input_event
from streamer_toolbox.core.widgets.widget_input import WidgetInput, check_input_name


class TestWidgetInput(unittest.TestCase):
    def test_what_the_code_hears_and_the_fields_of_a_custom_input(self) -> None:
        self.assertEqual(WidgetInput("chat").heard_as, "message")
        self.assertEqual(WidgetInput("lines", "chat", listener="chat-line").heard_as, "chat-line")
        custom = WidgetInput("progress", "custom", fields="done, goal goal,  2bad")
        self.assertEqual((custom.heard_as, custom.field_names), ("progress", ("done", "goal")))
        self.assertEqual(WidgetInput.from_dict(custom.to_dict()), custom)
        self.assertEqual(WidgetInput.from_dict({"name": "x", "kind": "nonsense"}).kind, "custom")
        with self.assertRaisesRegex(ValueError, "no spaces"):
            check_input_name("my input")

    def test_the_event_the_code_gets(self) -> None:
        event = input_event("chat", {"user": "Ann", "message": "hi", "platform": "rumble", "color": ""})
        self.assertEqual((event["service"], event["data"]["displayName"], event["data"]["text"]),
                         ("rumble", "Ann", "hi"))
        self.assertEqual(input_event("follow", {"user": "Kit"}), {"type": "follower", "name": "Kit"})
        self.assertEqual(input_event("custom", {"done": 3}), {"done": 3})


if __name__ == "__main__":
    unittest.main()
