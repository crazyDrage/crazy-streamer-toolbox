import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.fonts.font_reader import FontReader
from tests.fakes.tiny_font import TinyFont


class TestFontReader(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_what_the_file_says_about_itself(self) -> None:
        path = TinyFont.make(self.folder / "b.ttf", "Bangers", weight=700, italic=True, license="SIL OFL 1.1",
                             copyright="(c) Someone", fs_type=0x0002)
        face, = FontReader().read(path)
        self.assertEqual((face.family, face.weight, face.italic), ("Bangers", 700, True))
        self.assertEqual((face.license, face.copyright, face.no_embedding), ("SIL OFL 1.1", "(c) Someone", True))
        self.assertEqual(face.path, path)

    def test_a_file_that_is_no_font_gives_nothing(self) -> None:
        path = self.folder / "nope.ttf"
        path.write_bytes(b"not a font")
        self.assertEqual(FontReader().read(path), [])
