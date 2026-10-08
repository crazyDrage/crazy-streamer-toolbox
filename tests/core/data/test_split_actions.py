import unittest

from streamer_toolbox.core.data.box_value import kind_of, to_kind, understand
from streamer_toolbox.core.data.split_actions import SplitActions


class TestSplitActions(unittest.IsolatedAsyncioTestCase):
    async def test_split_understands_json_text_and_converts_to_the_set_kinds(self) -> None:
        data = '{"x": "0.5", "count": "3", "on": "true", "name": "Dragon", "tags": ["a"], "id": 7}'
        self.assertEqual(await SplitActions.split(data),  # no kinds set: every field as it came
                         {"x": "0.5", "count": "3", "on": "true", "name": "Dragon", "tags": ["a"], "id": 7})
        self.assertEqual(await SplitActions.split({"id": "12345", "n": 123456789012345678},
                                                  {"id": "any", "n": "number"}),
                         {"id": "12345", "n": 123456789012345678})  # an id stays text; every digit is kept
        self.assertEqual(await SplitActions.split(data, {"x": "text", "count": "number"}),
                         {"x": "0.5", "count": 3})

    async def test_split_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs an object"):
            await SplitActions.split("just text")
        with self.assertRaisesRegex(KeyError, "no field size"):
            await SplitActions.split({"x": 1}, {"size": "number"})
        with self.assertRaisesRegex(ValueError, "not a number"):
            await SplitActions.split({"x": "left"}, {"x": "number"})

    def test_kinds(self) -> None:
        # a value has the kind it came with: text that looks like a number (an id) is text
        self.assertEqual([kind_of(v) for v in (1.5, "3", "yes", "true", True, [1], '{"a": 1}', {"a": 1}, None)],
                         ["number", "text", "text", "text", "yes/no", "list", "text", "object", "any"])
        self.assertEqual((understand("1e3"), understand("7"), understand("nan")), (1000.0, 7, "nan"))
        self.assertEqual((to_kind("2.0", "number"), to_kind(5, "text"), to_kind("off", "yes/no")), (2, "5", False))
