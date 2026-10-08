import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

FILE = Path(__file__).parents[2] / "plugins" / "sammi_decks" / "lib" / "deck_layouts.py"
_spec = importlib.util.spec_from_file_location("sammi_decks_deck_layouts", FILE)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
DeckLayouts, color = _module.DeckLayouts, _module.color

# like SAMMI's json/decks_data.json: decks under "default", one stored encrypted (a string)
DATA = {"default": [
    {"unique_id": "d1", "deck_name": "sounds", "background_color": 4210752.0, "button_list": [
        {"button_id": "ID38", "text": "<-", "x": 0.0, "y": 0.9, "width": 0.1, "height": 0.1, "color": 12632256.0,
         "font_color": 16777215.0, "border": 2.0, "border_color": 0.0, "is_transparent": 0.0, "image": "",
         "stretch": 0.0},
        {"button_id": "lizard", "text": "lizard", "x": 0.2, "y": 0.1, "width": 0.3, "height": 0.2, "color": 255.0,
         "image": "lizard.png", "stretch": 1.0}]},
    "ggoNiiMNCkvrCgmd7goge6IJ"]}


class TestSammiDeckLayouts(unittest.TestCase):
    """The sammi_decks plugin's DeckLayouts (plugins/sammi_decks/lib/deck_layouts.py)."""

    def test_colours_are_blue_green_red(self) -> None:
        self.assertEqual(color(255), "#ff0000")
        self.assertEqual(color(12632256.0), "#c0c0c0")
        self.assertEqual(color(16711680), "#0000ff")

    def test_reads_spots_and_skips_encrypted_decks(self) -> None:
        layouts = DeckLayouts.parse(DATA)
        self.assertEqual(list(layouts), ["d1"])
        self.assertEqual(layouts["d1"]["background"], "#404040")
        lizard = layouts["d1"]["buttons"]["lizard"]
        self.assertEqual((lizard["x"], lizard["y"], lizard["w"], lizard["h"]), (0.2, 0.1, 0.3, 0.2))
        self.assertEqual((lizard["color"], lizard["image"], lizard["stretch"]), ("#ff0000", "lizard.png", True))

    def test_reads_sammis_folder_and_again_only_after_a_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "json").mkdir()
            path = Path(tmp) / "json" / "decks_data.json"
            path.write_text(json.dumps(DATA), encoding="utf-8")
            layouts = DeckLayouts()
            first = layouts.layouts(tmp)
            self.assertIs(layouts.layouts(tmp), first)  # unchanged file: not read again
            self.assertEqual(layouts.layouts(str(Path(tmp) / "nowhere")), {})
            self.assertEqual(layouts.layouts(""), {})
            self.assertIsNone(DeckLayouts.images(tmp))
