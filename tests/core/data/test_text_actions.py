import unittest

from streamer_toolbox.core.data.boxes.change_case import ChangeCase
from streamer_toolbox.core.data.boxes.join_list_to_text import JoinListToText
from streamer_toolbox.core.data.boxes.replace_in_text import ReplaceInText
from streamer_toolbox.core.data.boxes.split_text import SplitText
from streamer_toolbox.core.data.boxes.text_length import TextLength
from streamer_toolbox.core.data.boxes.trim_text import TrimText


class TestTextActions(unittest.IsolatedAsyncioTestCase):
    async def test_split_and_join(self) -> None:
        self.assertEqual(await SplitText().run("  ll   5 "), ["ll", "5"])
        self.assertEqual(await SplitText().run("a,,b", ","), ["a", "b"])
        self.assertEqual(await SplitText().run(""), [])
        self.assertEqual(await JoinListToText().run(["ll", 5], " "), "ll 5")
        self.assertEqual(await JoinListToText().run('["a", "b"]'), "a, b")

    async def test_replace_length_case_trim(self) -> None:
        self.assertEqual(await ReplaceInText().run("Lizard lizard", "lizard", "fox"), "Lizard fox")
        self.assertEqual(await ReplaceInText().run("Lizard lizard", "LIZARD", "fox", ignore_case="true"), "fox fox")
        self.assertEqual(await ReplaceInText().run("a.b", ".", "\\1"), "a\\1b")  # nothing is a pattern
        self.assertEqual(await TextLength().run("fän"), 3)
        self.assertEqual(await ChangeCase().run("Right Arm", "lower"), "right arm")
        self.assertEqual(await ChangeCase().run("right arm", "title"), "Right Arm")
        self.assertEqual(await TrimText().run("  hi \n"), "hi")
        with self.assertRaises(ValueError):
            await ChangeCase().run("x", "sideways")


if __name__ == "__main__":
    unittest.main()
