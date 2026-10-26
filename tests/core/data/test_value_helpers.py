import unittest

from streamer_toolbox.core.data.value_helpers import HELPERS, apply_helper, helpers_for
from streamer_toolbox.core.flows.box_wire import box_source, field_of


class TestValueHelpers(unittest.TestCase):
    def test_object_helpers(self) -> None:
        position = {"x": 0.5, "name": "Dragon", "items": [1, 2]}
        self.assertEqual(apply_helper("keys", position), ["x", "name", "items"])
        self.assertEqual(apply_helper("values", position), [0.5, "Dragon", [1, 2]])
        self.assertEqual(apply_helper("kinds", position), {"x": "number", "name": "text", "items": "list"})
        self.assertEqual(apply_helper("count", position), 3)
        self.assertEqual(apply_helper("kind", position), "object")
        self.assertEqual(apply_helper("text", position), '{"x": 0.5, "name": "Dragon", "items": [1, 2]}')

    def test_list_and_text_helpers(self) -> None:
        self.assertEqual(apply_helper("first", ["a", "b"]), "a")
        self.assertEqual(apply_helper("last", '["a", "b"]'), "b")  # JSON text counts as the list it holds
        self.assertEqual(apply_helper("kinds", [1, "a"]), ["number", "text"])
        self.assertEqual(apply_helper("count", "hello"), 5)

    def test_wrong_kind_or_name_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "@keys needs an object, not list"):
            apply_helper("keys", [1])
        with self.assertRaisesRegex(ValueError, "empty"):
            apply_helper("first", [])
        with self.assertRaisesRegex(KeyError, "unknown helper @size"):
            apply_helper("size", [1])
        self.assertEqual(set(HELPERS), {"keys", "values", "kinds", "count", "kind", "first", "last", "text"})

    def test_only_the_helpers_that_fit_a_known_kind_are_offered(self) -> None:
        self.assertEqual(helpers_for("text"), [])
        self.assertEqual(helpers_for("number"), [])
        self.assertEqual(helpers_for("object"), ["keys", "values", "kinds", "count", "text"])
        self.assertEqual(helpers_for("list"), ["kinds", "count", "first", "last", "text"])
        self.assertEqual(helpers_for(""), list(HELPERS))

    def test_a_wire_path_may_end_in_or_go_through_a_helper(self) -> None:
        self.assertEqual(box_source("${box.n3.items.@count}"), ("n3", "items.@count"))
        self.assertEqual(field_of({"items": [4, 5]}, "items.@last", "box n3"), 5)
        self.assertEqual(field_of({"items": [{"a": 1}]}, "items.@first.a", "box n3"), 1)


if __name__ == "__main__":
    unittest.main()
