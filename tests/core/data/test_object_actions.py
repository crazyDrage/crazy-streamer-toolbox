import unittest

from streamer_toolbox.core.data.boxes.build_object import BuildObject
from streamer_toolbox.core.data.boxes.get_from_object import GetFromObject
from streamer_toolbox.core.data.boxes.object_has_key import ObjectHasKey
from streamer_toolbox.core.data.boxes.object_keys import ObjectKeys
from streamer_toolbox.core.data.boxes.object_values import ObjectValues
from streamer_toolbox.core.data.boxes.remove_from_object import RemoveFromObject
from streamer_toolbox.core.data.boxes.set_in_object import SetInObject

SETTINGS = {"right_arm": {"id": 0, "bool": False}, "left_arm": {"id": 1, "bool": True}}


class TestObjectActions(unittest.IsolatedAsyncioTestCase):
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
        built = await BuildObject().run(name_1="id", value_1=3, name_2="bool", value_2=True, name_3=" ",
                                          value_3="left out")
        self.assertEqual(built, {"id": 3, "bool": True})
        self.assertEqual(await BuildObject().run(start={"a": 1}, name_1="b", value_1=2), {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()
