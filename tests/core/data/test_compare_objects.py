import unittest

from streamer_toolbox.core.data.boxes.compare_objects import CompareObjects

BEFORE = {"model": "Lizard", "physics": {"wind": 0, "strength": 50}, "hotkeys": {"Wave": {"keys": "N1"}},
          "tags": ["a"]}
AFTER = {"model": "Lizard", "physics": {"wind": 20, "strength": 50}, "hotkeys": {"Wave": {"keys": "N1"},
                                                                                 "Spin": {"keys": "N2"}},
         "tags": ["a", "b"]}


class TestCompareObjects(unittest.IsolatedAsyncioTestCase):
    async def test_changed_gives_before_and_after_by_path(self) -> None:
        result = await CompareObjects().run(BEFORE, AFTER)
        self.assertEqual(result["values"], {"physics.wind": {"before": 0, "after": 20},
                                            "tags": {"before": ["a"], "after": ["a", "b"]},
                                            "hotkeys.Spin.keys": {"before": None, "after": "N2"}})
        self.assertEqual(result["keys"], ["physics.wind", "tags", "hotkeys.Spin.keys"])
        self.assertTrue(result["changed"])

    async def test_same_and_all(self) -> None:
        same = await CompareObjects().run(BEFORE, AFTER, show="same")
        self.assertEqual(same["values"], {"model": "Lizard", "physics.strength": 50, "hotkeys.Wave.keys": "N1"})
        everything = await CompareObjects().run(BEFORE, AFTER, show="all")
        self.assertEqual(len(everything["values"]), 6)
        self.assertEqual(everything["values"]["model"], {"before": "Lizard", "after": "Lizard", "changed": False})
        self.assertTrue(everything["values"]["physics.wind"]["changed"])

    async def test_nothing_changed_and_a_key_that_is_gone(self) -> None:
        self.assertFalse((await CompareObjects().run(BEFORE, dict(BEFORE)))["changed"])
        gone = await CompareObjects().run({"a": None}, {})  # gone, even if it was empty
        self.assertEqual(gone["values"], {"a": {"before": None, "after": None}})
        first = await CompareObjects().run("", AFTER)  # nothing saved yet: everything is new
        self.assertEqual(len(first["keys"]), 6)
        self.assertEqual((await CompareObjects().run('{"a": 1}', '{"a": 2}'))["keys"], ["a"])  # JSON text works

    async def test_a_wrong_choice_is_said(self) -> None:
        with self.assertRaisesRegex(ValueError, "changed, same, all"):
            await CompareObjects().run({}, {}, show="diff")


if __name__ == "__main__":
    unittest.main()
