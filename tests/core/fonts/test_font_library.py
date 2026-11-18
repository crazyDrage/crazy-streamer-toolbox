import json
import tempfile
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._f_v_a_r import Axis, table__f_v_a_r

from streamer_toolbox.core.fonts.font_face import FontFace
from streamer_toolbox.core.fonts.font_library import FontLibrary
from streamer_toolbox.core.fonts.kept_font import KeptFont
from tests.fakes.tiny_font import TinyFont


class TestFontLibrary(unittest.TestCase):
    """His 11-18: a fonts folder (upload or put files there), fonts of this PC by name, every font marked."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.by_name = self.root / "fonts.json"
        self.by_name.write_text(json.dumps({"this_machine": []}), encoding="utf-8")
        self.library = FontLibrary(self.root / "fonts", self.by_name)
        self.source = self.root / "source"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _font(self, name: str, family: str, **kwargs) -> bytes:
        return TinyFont.make(self.source / name, family, **kwargs).read_bytes()

    def test_an_uploaded_file_is_hosted_and_a_name_is_this_machine_only(self) -> None:
        self.assertEqual(self.library.add_file("Bangers-Regular.ttf", self._font("b.ttf", "Bangers")), "Bangers")
        self.library.add_file("Bangers-Bold.ttf", self._font("bb.ttf", "Bangers", weight=700))
        self.library.add_by_name("Impact")
        self.library.add_by_name("impact")  # once
        self.assertEqual(self.library.fonts(), [
            KeptFont("Bangers", True, ("Bangers-Bold.ttf", "Bangers-Regular.ttf")), KeptFont("Impact", False)])
        self.assertEqual(KeptFont("Impact", False).mark, "On this machine only")
        self.assertEqual(KeptFont("Bangers", True).mark, "All devices")

    def test_a_file_put_in_the_folder_by_hand_shows_up(self) -> None:
        TinyFont.make(self.library.folder / "Orbitron.ttf", "Orbitron")
        self.assertEqual([f.family for f in self.library.fonts()], ["Orbitron"])

    def test_the_add_list_leaves_out_fonts_already_added(self) -> None:
        self.library.add_file("Bangers-Regular.ttf", self._font("b.ttf", "Bangers"))
        self.library.add_by_name("Impact")
        pc = {name: [FontFace(name, Path(f"{name}.ttf"))] for name in ("Arial", "bangers", "IMPACT", "Orbitron")}
        self.assertEqual(list(self.library.not_added(pc)), ["Arial", "Orbitron"])

    def test_what_is_not_taken(self) -> None:
        with self.assertRaises(ValueError):
            self.library.add_file("virus.exe", b"MZ")
        with self.assertRaises(ValueError):
            self.library.add_file("fake.ttf", b"not a font")
        self.assertEqual(list(self.library.folder.glob("*")), [])  # the bad file didn't stay

    def test_same_name_twice_keeps_both_and_odd_names_are_made_safe(self) -> None:
        data = self._font("b.ttf", "Bangers")
        self.library.add_file("../../evil name?.ttf", data)
        self.library.add_file("evil name_.ttf", data)
        self.assertEqual(sorted(p.name for p in self.library.folder.glob("*")),
                         ["evil name_ (2).ttf", "evil name_.ttf"])

    def test_the_endpoint_gets_only_files_of_the_folder(self) -> None:
        self.library.add_file("Bangers.ttf", self._font("b.ttf", "Bangers"))
        self.assertEqual(self.library.file("Bangers.ttf"), self.library.folder / "Bangers.ttf")
        for name in ("../fonts.json", "fonts.json", "nope.ttf", "Bangers.ttf/.."):
            self.assertIsNone(self.library.file(name), name)

    def test_css_has_a_font_face_per_hosted_file(self) -> None:
        self.library.add_file("Bangers Bold.ttf", self._font("b.ttf", "Bangers", weight=700, italic=True))
        self.library.add_by_name("Impact")
        css = self.library.css()
        self.assertIn('font-family: "Bangers"; src: url("/toolbox/fonts/file/Bangers%20Bold.ttf") '
                      'format("truetype"); font-weight: 700; font-style: italic;', css)
        self.assertNotIn("Impact", css)  # found by name on this PC, never hosted

    def test_remove_deletes_its_files_or_takes_the_name_out(self) -> None:
        self.library.add_file("Bangers.ttf", self._font("b.ttf", "Bangers"))
        self.library.add_by_name("Impact")
        self.assertEqual(self.library.remove("Bangers"), ["Bangers.ttf"])
        self.assertEqual(self.library.remove("Impact"), ["Impact"])
        self.assertEqual(self.library.fonts(), [])

    def test_copy_from_this_pc_only_when_allowed(self) -> None:
        own = TinyFont.make(self.source / "orbitron.ttf", "Orbitron", license="SIL Open Font License")
        self.assertEqual(self.library.copy_installed([FontFace("Orbitron", own)]), "Orbitron")
        windows = TinyFont.make(self.source / "impact.ttf", "Impact")
        with self.assertRaises(ValueError):
            self.library.copy_installed([FontFace("Impact", windows)])
        self.assertEqual([f.family for f in self.library.fonts()], ["Orbitron"])

    def test_a_broken_name_list_means_none(self) -> None:
        self.by_name.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.library.fonts(), [])

    def test_a_variable_font_has_all_its_weights(self) -> None:
        path = TinyFont.make(self.library.folder / "Var.ttf", "Var")
        font = TTFont(str(path))
        fvar = table__f_v_a_r()
        axis = Axis()
        axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue, axis.axisNameID = "wght", 400, 400, 900, 256
        fvar.axes, fvar.instances = [axis], []
        font["fvar"] = fvar
        font.save(str(path))
        self.assertIn("font-weight: 400 900;", self.library.css())
