import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.testing.test_item import BOX, PAGE, TOOL, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS, TestList
from streamer_toolbox.devtools.tested.test_window import TestWindow

ITEMS = [TestItem(PAGE, "/variables", "Variables", "Variables", file="variables/page", heading="Variables"),
         TestItem(BOX, "obs.mute", "Mute", "OBS", "Audio", "flows/boxes/obs/audio", "Flows > Boxes > OBS > Audio"),
         TestItem(BOX, "obs.get_scene", "Get scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
                  "Flows > Boxes > OBS > Scenes"),
         TestItem(BOX, "obs.set_scene", "Set scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
                  "Flows > Boxes > OBS > Scenes"),
         TestItem(TOOL, "points", "Points", file="tools/points", heading="Tools > Points")]


class TestTestWindow(unittest.TestCase):
    """What the test window lists and where Back / Next go. It reads the record's files only, as it does when
    it runs next to the toolbox; the drawing itself needs a browser."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "tested"
        TestList(self.folder).sync(ITEMS)
        self.window = TestWindow(lambda: TestList(self.folder))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _tick(self, key: str) -> None:
        for check in CHECKS:
            self.window._tested.set_check(key, check, True)

    def test_lists_the_files_in_the_menus_order_without_the_toolbox(self) -> None:
        self.assertEqual(self.window.files(), {
            "variables/page": ["page:/variables"], "flows/boxes/obs/audio": ["box:obs.mute"],
            "flows/boxes/obs/scenes": ["box:obs.get_scene", "box:obs.set_scene"], "tools/points": ["tool:points"]})
        self.assertEqual(self.window._option("flows/boxes/obs/scenes", self.window.files()["flows/boxes/obs/scenes"]),
                         "Flows > Boxes > OBS > Scenes  ·  2 open")

    def test_a_box_shows_the_number_of_its_test_flow(self) -> None:
        self.assertEqual([self.window.number(key) for key in ("box:obs.mute", "box:obs.set_scene", "tool:points")],
                         ["001", "003", ""])

    def test_a_tick_is_in_the_file_and_only_open_leaves_the_tested_out(self) -> None:
        self._tick("box:obs.mute")
        self._tick("box:obs.get_scene")
        text = (self.folder / "flows" / "boxes" / "obs" / "audio.md").read_text(encoding="utf-8")
        self.assertIn("| Mute | `obs.mute` | - | yes | yes | yes |", text)
        self.assertEqual(self.window._option("flows/boxes/obs/audio", ["box:obs.mute"]),
                         "Flows > Boxes > OBS > Audio  ✓")
        self.window._only_open = True
        self.assertEqual(self.window.files(), {
            "variables/page": ["page:/variables"], "flows/boxes/obs/scenes": ["box:obs.set_scene"],
            "tools/points": ["tool:points"]})
        again = TestWindow(lambda: TestList(self.folder))  # Reload, or the window opened anew
        self.assertTrue(again._tested.tested("box:obs.mute"))
        self.assertEqual(list(again.files()), list(TestList(self.folder).files()))

    def test_next_and_back_go_through_the_files_and_stay_at_the_ends(self) -> None:
        self.window.step(-1)
        self.assertEqual(self.window._where, "variables/page")
        self.window.step(1)
        self.window.step(1)
        self.assertEqual(self.window._where, "flows/boxes/obs/scenes")
        self.window.step(1)
        self.window.step(1)
        self.assertEqual(self.window._where, "tools/points")

    def test_search_looks_through_everything(self) -> None:
        self.window._search = "obs scene"
        self.assertEqual(self.window.found(), {"flows/boxes/obs/scenes": ["box:obs.get_scene", "box:obs.set_scene"]})
        self.window._search = "points"
        self.assertEqual(self.window.found(), {"tools/points": ["tool:points"]})
        self.window._search = "nothing like it"
        self.assertEqual(self.window.found(), {})

    def test_a_row_of_what_is_gone_is_not_shown_and_stays_marked(self) -> None:
        TestList(self.folder).sync([item for item in ITEMS if item.id != "obs.mute"])
        window = TestWindow(lambda: TestList(self.folder))
        self.assertNotIn("flows/boxes/obs/audio", window.files())
        window._tested.set_note("box:obs.mute", "kept")  # writing that file keeps the mark
        self.assertIn("| Mute (not in the toolbox any more) | `obs.mute` |",
                      (self.folder / "flows" / "boxes" / "obs" / "audio.md").read_text(encoding="utf-8"))
        self.assertIn("| **All** | **0** | **4** |", (self.folder / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
