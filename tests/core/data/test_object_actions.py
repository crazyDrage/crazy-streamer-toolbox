import unittest

from streamer_toolbox.core.data.boxes.build_object import BuildObject
from streamer_toolbox.core.data.boxes.get_from_object import GetFromObject
from streamer_toolbox.core.data.boxes.join_objects import JoinObjects
from streamer_toolbox.core.data.boxes.object_has_key import ObjectHasKey
from streamer_toolbox.core.data.boxes.object_keys import ObjectKeys
from streamer_toolbox.core.data.boxes.object_values import ObjectValues
from streamer_toolbox.core.data.boxes.remove_from_object import RemoveFromObject
from streamer_toolbox.core.data.boxes.set_in_object import SetInObject

SETTINGS = {"right_arm": {"id": 0, "bool": False}, "left_arm": {"id": 1, "bool": True}}


class TestObjectActions(unittest.IsolatedAsyncioTestCase):
    async def test_join_two_objects_the_second_wins(self) -> None:
        """His 11-16: "a different dict, and then add the 2 dicts together"."""
        first, second = {"Kappa": "bttv", "catJAM": "bttv"}, {"Kappa": "twitch"}
        self.assertEqual({"Kappa": "twitch", "catJAM": "bttv"}, await JoinObjects().run(first, second))
        self.assertEqual({"Kappa": "bttv", "catJAM": "bttv"}, first)  # the two stay as they were
        self.assertEqual({"a": 1}, await JoinObjects().run('{"a": 1}', ""))
        self.assertEqual({}, await JoinObjects().run())

    async def test_get_by_key_or_path(self) -> None:
        self.assertEqual(await GetFromObject().run(SETTINGS, "left_arm"), {"id": 1, "bool": True})
        self.assertEqual(await GetFromObject().run(SETTINGS, "left_arm.id"), 1)
        self.assertEqual(await GetFromObject().run('{"a.b": 2}', "a.b"), 2)  # a key with a dot in it
        self.assertEqual(await GetFromObject().run(SETTINGS, "tail", default="none"), "none")
        self.assertEqual(await GetFromObject().run({"ll": "left_leg", "LL": "exact"}, "LL"), "exact")
        self.assertEqual(await GetFromObject().run({"ll": "left_leg"}, "LL"), "left_leg")
        self.assertTrue(await ObjectHasKey().run({"ll": 1}, "Ll"))
        with self.assertRaisesRegex(KeyError, "has: right_arm, left_arm"):
            await GetFromObject().run(SETTINGS, "tail")

    async def test_has_keys_values(self) -> None:
        self.assertTrue(await ObjectHasKey().run(SETTINGS, "right_arm.bool"))
        self.assertFalse(await ObjectHasKey().run(SETTINGS, "tail"))
        self.assertEqual(await ObjectKeys().run(SETTINGS), ["right_arm", "left_arm"])
        self.assertEqual(await ObjectValues().run({"a": 1, "b": 2}), {"a": 1, "b": 2})  # a dot per key (round 60)
        self.assertEqual(await ObjectKeys().run(""), [])

    async def test_set_and_remove_give_a_new_object(self) -> None:
        changed = await SetInObject().run(SETTINGS, "right_arm.bool", True)
        self.assertTrue(changed["right_arm"]["bool"])
        self.assertFalse(SETTINGS["right_arm"]["bool"])  # the original stays as it was
        self.assertEqual(await SetInObject().run("", "tail", {"id": 4}), {"tail": {"id": 4}})
        self.assertEqual(await RemoveFromObject().run(SETTINGS, "right_arm"), {"left_arm": {"id": 1, "bool": True}})
        with self.assertRaisesRegex(ValueError, "not an object"):
            await SetInObject().run(SETTINGS, "right_arm.id.x", 1)

    async def test_build(self) -> None:
        """His 11-22: lines he names (named_lines), no start object (Join objects does that)."""
        inner = {"x": 1}
        built = await BuildObject().run(id=3, bool=True, inner=inner)
        self.assertEqual(built, {"id": 3, "bool": True, "inner": {"x": 1}})
        built["inner"]["x"] = 2
        self.assertEqual(inner, {"x": 1})  # what was wired in stays as it was
        self.assertEqual(await BuildObject().run(), {})
        self.assertTrue(BuildObject.named_lines)
        self.assertTrue(BuildObject.data_only)


if __name__ == "__main__":
    unittest.main()
