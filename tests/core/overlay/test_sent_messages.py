import unittest

from streamer_toolbox.core.overlay.sent_messages import SentMessages


class TestSentMessages(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 0.0
        self.sent = SentMessages(max_age=60, keep=3, clock=lambda: self.now)

    def test_numbers_go_up_and_hello_says_the_newest(self) -> None:
        self.assertEqual(self.sent.stamp({"type": "clear"}), {"type": "clear", "id": 1})
        self.assertEqual(self.sent.stamp({"type": "clear"})["id"], 2)
        self.assertEqual(self.sent.hello(), {"type": "hello", "run": self.sent.run, "last": 2})

    def test_what_came_after_the_last_id_younger_than_max_age(self) -> None:
        self.sent.stamp({"type": "a"})
        self.now = 50
        self.sent.stamp({"type": "b"})
        self.sent.stamp({"type": "c"})
        self.now = 70  # "a" is 70 s old now
        self.assertEqual([m["type"] for m in self.sent.since(self.sent.run, 0)], ["b", "c"])
        self.assertEqual([m["type"] for m in self.sent.since(self.sent.run, 2)], ["c"])
        self.assertEqual([m["type"] for m in self.sent.since("before a restart", 9)], ["b", "c"])

    def test_only_the_last_few_are_kept(self) -> None:
        for kind in "abcd":
            self.sent.stamp({"type": kind})
        self.assertEqual([m["type"] for m in self.sent.since(self.sent.run, 0)], ["b", "c", "d"])

    def test_a_widget_page_gets_its_own_and_those_for_every_page(self) -> None:
        self.sent.stamp({"type": "event"}, "goal")
        self.sent.stamp({"type": "event"}, "chat_box")
        self.sent.stamp({"type": "session"})
        self.assertEqual([m["id"] for m in self.sent.since(self.sent.run, 0, "goal")], [1, 3])


if __name__ == "__main__":
    unittest.main()
