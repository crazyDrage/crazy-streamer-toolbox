import unittest

from streamer_toolbox.core.data.object_actions import ObjectActions

SETTINGS = {"right_arm": {"id": 0, "bool": False}, "left_arm": {"id": 1, "bool": True}}


class TestObjectActions(unittest.IsolatedAsyncioTestCase):
    async def test_get_by_key_or_path(self) -> None:
        self.assertEqual(await ObjectActions.get(SETTINGS, "left_arm"), {"id": 1, "bool": True})
        self.assertEqual(await ObjectActions.get(SETTINGS, "left_arm.id"), 1)
        self.assertEqual(await ObjectActions.get('{"a.b": 2}', "a.b"), 2)  # a key with a dot in it
        self.assertEqual(await ObjectActions.get(SETTINGS, "tail", default="none"), "none")
        self.assertEqual(await ObjectActions.get({"ll": "left_leg", "LL": "exact"}, "LL"), "exact")
        self.assertEqual(await ObjectActions.get({"ll": "left_leg"}, "LL"), "left_leg")
        self.assertTrue(await ObjectActions.has({"ll": 1}, "Ll"))
        with self.assertRaisesRegex(KeyError, "has: right_arm, left_arm"):
            await ObjectActions.get(SETTINGS, "tail")

    async def test_has_keys_values(self) -> None:
        self.assertTrue(await ObjectActions.has(SETTINGS, "right_arm.bool"))
        self.assertFalse(await ObjectActions.has(SETTINGS, "tail"))
        self.assertEqual(await ObjectActions.keys(SETTINGS), ["right_arm", "left_arm"])
        self.assertEqual(await ObjectActions.values({"a": 1, "b": 2}), [1, 2])
        self.assertEqual(await ObjectActions.keys(""), [])

    async def test_set_and_remove_give_a_new_object(self) -> None:
        changed = await ObjectActions.set(SETTINGS, "right_arm.bool", True)
        self.assertTrue(changed["right_arm"]["bool"])
        self.assertFalse(SETTINGS["right_arm"]["bool"])  # the original stays as it was
        self.assertEqual(await ObjectActions.set("", "tail", {"id": 4}), {"tail": {"id": 4}})
        self.assertEqual(await ObjectActions.remove(SETTINGS, "right_arm"), {"left_arm": {"id": 1, "bool": True}})
        with self.assertRaisesRegex(ValueError, "not an object"):
            await ObjectActions.set(SETTINGS, "right_arm.id.x", 1)

    async def test_build(self) -> None:
        built = await ObjectActions.build(name_1="id", value_1=3, name_2="bool", value_2=True, name_3=" ",
                                          value_3="left out")
        self.assertEqual(built, {"id": 3, "bool": True})
        self.assertEqual(await ObjectActions.build(start={"a": 1}, name_1="b", value_1=2), {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()
