import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.testing.test_item import BOX, TRIGGER, TestItem
from streamer_toolbox.devtools.tested.tried_page import TriedPage


class TestTriedPage(unittest.TestCase):
    """The manual's public list: only what has at least one of his checks, with each check shown."""

    def test_only_tried_things_with_their_checks(self) -> None:
        items = [TestItem(BOX, "warudo.send", "Send action to Warudo", heading="Flows > Boxes > Warudo"),
                 TestItem(BOX, "warudo.raw", "Send raw message to Warudo", heading="Flows > Boxes > Warudo"),
                 TestItem(TRIGGER, "warudo.message", "Message from Warudo", heading="Flows > Triggers > Warudo")]
        checks = {"box:warudo.send": {"works": True, "understandable": True, "usable": True},
                  "trigger:warudo.message": {"works": True, "understandable": False, "usable": False}}
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "user" / "tried.md"
            count = TriedPage(file).write(items, lambda key: checks.get(key, {"works": False}))
            text = file.read_text(encoding="utf-8")
        self.assertEqual(2, count)
        self.assertIn("| Send action to Warudo | Flows > Boxes > Warudo | yes | yes | yes |", text)
        self.assertIn("| Message from Warudo | Flows > Triggers > Warudo | yes | - | - |", text)
        self.assertNotIn("Send raw message", text)
        self.assertLess(text.index("## Triggers"), text.index("## Boxes"))


if __name__ == "__main__":
    unittest.main()
