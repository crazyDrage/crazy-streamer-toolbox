import unittest

from streamer_toolbox.gui.components.flow_editor.node_editor import _move_key


class TestMoveKey(unittest.TestCase):
    """End's named lines move up and down (his round 59); its own fields stay where they are."""

    def test_a_line_trades_places_with_its_neighbour(self) -> None:
        params = {"name": "x", "user": "${box.start.user}", "amount": 5, "text": "hi"}
        _move_key(params, "text", -1, ["user", "amount", "text"])
        self.assertEqual(list(params.items()), [("name", "x"), ("user", "${box.start.user}"), ("text", "hi"),
                                                ("amount", 5)])
        _move_key(params, "user", +1, ["user", "text", "amount"])
        self.assertEqual(list(params), ["name", "text", "user", "amount"])

    def test_the_ends_dont_move_further(self) -> None:
        params = {"a": 1, "b": 2}
        _move_key(params, "a", -1, ["a", "b"])
        _move_key(params, "b", +1, ["a", "b"])
        self.assertEqual(list(params), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
