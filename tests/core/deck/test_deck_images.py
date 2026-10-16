import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.deck.deck_images import DeckImages


class TestDeckImages(unittest.TestCase):
    def test_keeps_a_picture_under_a_safe_name_and_numbers_another_with_that_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            images = DeckImages(Path(tmp) / "deck_images")
            self.assertEqual(images.add("C:\\pics\\my lizard!.PNG", b"one"), "my_lizard_.png")
            self.assertEqual(images.add("my lizard!.png", b"one"), "my_lizard_.png")  # the same file again
            self.assertEqual(images.add("my lizard!.png", b"two"), "my_lizard__2.png")
            self.assertEqual((images.folder / "my_lizard__2.png").read_bytes(), b"two")
            self.assertEqual(images.url("my_lizard_.png"), "/deck-images/my_lizard_.png")

    def test_refuses_what_is_no_picture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            images = DeckImages(Path(tmp))
            for name in ("drawing.svg", "run.exe", "noname"):
                with self.assertRaises(ValueError):
                    images.add(name, b"x")
