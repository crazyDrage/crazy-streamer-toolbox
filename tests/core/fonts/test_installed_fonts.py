import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.fonts.font_face import FontFace
from streamer_toolbox.core.fonts.installed_fonts import InstalledFonts
from tests.fakes.tiny_font import TinyFont


class TestInstalledFonts(unittest.TestCase):
    """His 11-18 + temp/research/21: fonts that came with Windows stay on this machine; one he installed himself
    may be copied in, unless its file forbids embedding."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_families_of_the_font_folders(self) -> None:
        TinyFont.make(self.folder / "orbitron.ttf", "Orbitron")
        TinyFont.make(self.folder / "sub" / "orbitron-bold.ttf", "Orbitron", weight=700)
        TinyFont.make(self.folder / "arial.ttf", "Arial")
        (self.folder / "readme.txt").write_text("not a font", encoding="utf-8")
        families = InstalledFonts([self.folder, self.folder / "missing"]).families()
        self.assertEqual(list(families), ["Arial", "Orbitron"])
        self.assertEqual(sorted(f.weight for f in families["Orbitron"]), [400, 700])

    def test_what_comes_with_windows(self) -> None:
        here = self.folder / "x.ttf"
        self.assertTrue(InstalledFonts.comes_with_windows(FontFace("Impact", here)))
        self.assertTrue(InstalledFonts.comes_with_windows(FontFace("Some Office Font", here,
                                                                   license="Microsoft supplied font.")))
        self.assertFalse(InstalledFonts.comes_with_windows(FontFace("Orbitron", here, license="SIL OFL")))

    def test_what_may_be_copied_into_the_toolbox(self) -> None:
        self.assertTrue(InstalledFonts.copyable(FontFace("Orbitron", self.folder / "o.ttf")))
        self.assertTrue(InstalledFonts.copyable(FontFace("Orbitron", self.folder / "o.otf")))
        self.assertFalse(InstalledFonts.copyable(FontFace("Impact", self.folder / "impact.ttf")))
        self.assertFalse(InstalledFonts.copyable(FontFace("Locked", self.folder / "l.ttf", no_embedding=True)))
        self.assertFalse(InstalledFonts.copyable(FontFace("Many", self.folder / "m.ttc")))
