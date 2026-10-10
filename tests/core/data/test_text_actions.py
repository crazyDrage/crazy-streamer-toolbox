import unittest

from streamer_toolbox.core.data.text_actions import TextActions


class TestTextActions(unittest.IsolatedAsyncioTestCase):
    async def test_split_and_join(self) -> None:
        self.assertEqual(await TextActions.split("  ll   5 "), ["ll", "5"])
        self.assertEqual(await TextActions.split("a,,b", ","), ["a", "b"])
        self.assertEqual(await TextActions.split(""), [])
        self.assertEqual(await TextActions.join(["ll", 5], " "), "ll 5")
        self.assertEqual(await TextActions.join('["a", "b"]'), "a, b")

    async def test_replace_length_case_trim(self) -> None:
        self.assertEqual(await TextActions.replace("Lizard lizard", "lizard", "fox"), "Lizard fox")
        self.assertEqual(await TextActions.replace("Lizard lizard", "LIZARD", "fox", ignore_case="true"), "fox fox")
        self.assertEqual(await TextActions.replace("a.b", ".", "\\1"), "a\\1b")  # nothing is a pattern
        self.assertEqual(await TextActions.length("fän"), 3)
        self.assertEqual(await TextActions.case("Right Arm", "lower"), "right arm")
        self.assertEqual(await TextActions.case("right arm", "title"), "Right Arm")
        self.assertEqual(await TextActions.trim("  hi \n"), "hi")
        with self.assertRaises(ValueError):
            await TextActions.case("x", "sideways")


if __name__ == "__main__":
    unittest.main()
