import unittest

from streamer_toolbox.core.files.file_types import IMAGE_TYPES
from streamer_toolbox.core.values.value_kind import ValueKind
from streamer_toolbox.core.values.value_kinds import ValueKinds


class TestValueKinds(unittest.TestCase):
    def setUp(self) -> None:
        self.kinds = ValueKinds()

    def test_the_global_kinds_are_always_there(self) -> None:
        self.assertEqual(self.kinds.names(), ["color", "file", "folder", "image", "list", "media", "number",
                                              "object", "sound", "text", "video", "whole_number", "yes_no"])
        self.assertEqual((self.kinds.get("color").extra, self.kinds.get("image").extra), ("colors", "files"))
        self.assertEqual(self.kinds.get("image").setting, IMAGE_TYPES)
        self.assertEqual((self.kinds.get("yes_no").annotation, self.kinds.get("yes_no").default), (bool, False))

    def test_a_special_kind_is_added_by_name(self) -> None:
        async def scenes() -> list[str]:
            return ["desktop"]

        kinds = ValueKinds([ValueKind("obs.scene", "OBS scene", extra="options", setting=scenes)])
        self.assertIn("obs.scene", kinds)
        self.assertIs(kinds.get("obs.scene").setting, scenes)
        with self.assertRaisesRegex(ValueError, "already there"):
            kinds.add(ValueKind("color", "Another colour"))
        with self.assertRaisesRegex(ValueError, "already there"):
            kinds.add(ValueKind("choice", "Choice"))
        with self.assertRaisesRegex(ValueError, "unknown value kind 'vts.animation'"):
            self.kinds.get("vts.animation")

    def test_what_is_sent(self) -> None:
        self.assertEqual(self.kinds.get("text").sent("hello"), "hello")
        self.assertEqual(self.kinds.get("number").sent("0.5"), 0.5)
        self.assertEqual(self.kinds.get("number").sent("3"), 3)
        self.assertIsInstance(self.kinds.get("number").sent(3.0), int)
        self.assertEqual(self.kinds.get("whole_number").sent("-1"), -1)
        self.assertEqual(self.kinds.get("yes_no").sent("no"), False)
        self.assertEqual(self.kinds.get("yes_no").sent(True), True)
        self.assertEqual(self.kinds.get("list").sent("[1, 2]"), [1, 2])
        self.assertEqual(self.kinds.get("list").sent(["a"]), ["a"])
        self.assertEqual(self.kinds.get("object").sent('{"x": 1}'), {"x": 1})

    def test_a_value_that_does_not_fit_is_refused(self) -> None:
        for kind, value in (("number", "many"), ("number", True), ("whole_number", "1.5"), ("yes_no", "maybe"),
                            ("list", "{}"), ("list", "a, b"), ("object", "[1]")):
            with self.subTest(kind=kind, value=value), self.assertRaises(ValueError):
                self.kinds.get(kind).sent(value)


if __name__ == "__main__":
    unittest.main()
