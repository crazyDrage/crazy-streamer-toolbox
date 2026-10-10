import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, PAGE, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import TESTING_FOLDER, TestList

ITEMS = [TestItem(PAGE, "/variables", "Variables", "Variables", file="variables/page", heading="Variables"),
         TestItem(TRIGGER, "timer", "Timer", "Toolbox", file="flows/triggers/toolbox",
                  heading="Flows > Triggers > Toolbox"),
         TestItem(BOX, "obs.mute", "Mute", "OBS", "Audio", "flows/boxes/obs/audio", "Flows > Boxes > OBS > Audio"),
         TestItem(BOX, "obs.get_scene", "Get scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
                  "Flows > Boxes > OBS > Scenes"),
         TestItem(BOX, "obs.set_scene", "Set scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
                  "Flows > Boxes > OBS > Scenes"),
         TestItem(TOOL, "points", "Points", file="tools/points", heading="Tools > Points"),
         TestItem(CONNECTION, "obs", "OBS", file="connections/obs", heading="Connections > OBS")]
HEAD = ["| What | Name in the code | AI checked | Works | Understandable | Usable | Last change | Note |",
        "|---|---|---|---|---|---|---|---|"]


class TestTestList(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "testing"
        self.day = date(2026, 10, 7)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _list(self) -> TestList:
        return TestList(self.folder, lambda: self.day)

    def _text(self, path: str) -> str:
        return (self.folder / path).read_text(encoding="utf-8")

    def _files(self) -> list[str]:
        return sorted(p.relative_to(self.folder).as_posix() for p in self.folder.rglob("*.md"))

    def test_sync_writes_a_row_for_everything_sorted_like_the_menu(self) -> None:
        self._list().sync(ITEMS)
        self.assertEqual(self._files(), [
            "README.md", "connections/obs.md", "flows/boxes/obs/audio.md", "flows/boxes/obs/scenes.md",
            "flows/triggers/toolbox.md", "tools/points.md", "variables/page.md"])
        self.assertEqual(self._text("flows/boxes/obs/scenes.md"), "\n".join([
            "# Flows > Boxes > OBS > Scenes", "", *HEAD,
            "| Get scene | `obs.get_scene` | - | - | - | - | - |  |",
            "| Set scene | `obs.set_scene` | - | - | - | - | - |  |", ""]))
        self.assertEqual("\n".join(line for line in self._text("README.md").splitlines() if line.startswith("| ")),
                         "\n".join(["| Where | Tested | Of |",
                                    "| **[variables](variables/)** | **0** | **1** |",
                                    "| [variables/page](variables/page.md) | 0 | 1 |",
                                    "| **[flows](flows/)** | **0** | **4** |",
                                    "| [flows/triggers/toolbox](flows/triggers/toolbox.md) | 0 | 1 |",
                                    "| [flows/boxes/obs/audio](flows/boxes/obs/audio.md) | 0 | 1 |",
                                    "| [flows/boxes/obs/scenes](flows/boxes/obs/scenes.md) | 0 | 2 |",
                                    "| **[tools](tools/)** | **0** | **1** |",
                                    "| [tools/points](tools/points.md) | 0 | 1 |",
                                    "| **[connections](connections/)** | **0** | **1** |",
                                    "| [connections/obs](connections/obs.md) | 0 | 1 |",
                                    "| **All** | **0** | **7** |"]))

    def test_take_writes_nothing_but_a_tick_finds_its_file(self) -> None:
        tested = self._list()
        tested.take(ITEMS)
        self.assertFalse(self.folder.exists())
        tested.set_check("tool:points", "works", True)
        self.assertEqual(self._files(), ["README.md", "tools/points.md"])

    def test_tested_needs_all_three_checks_and_is_read_back_from_the_text(self) -> None:
        tested = self._list()
        tested.sync(ITEMS)
        tested.set_check("box:obs.set_scene", "works", True)
        tested.set_check("box:obs.set_scene", "understandable", True)
        self.assertFalse(tested.tested("box:obs.set_scene"))
        self.day = date(2026, 10, 9)
        tested.set_check("box:obs.set_scene", "usable", True)
        tested.set_note("box:obs.set_scene", "the scene list | was\nslow once")
        self.assertTrue(tested.tested("box:obs.set_scene"))
        self.assertIn(
            "| Set scene | `obs.set_scene` | - | yes | yes | yes | 2026-10-09 | the scene list / was slow once |",
            self._text("flows/boxes/obs/scenes.md"))
        self.assertIn("| [flows/boxes/obs/scenes](flows/boxes/obs/scenes.md) | 1 | 2 |", self._text("README.md"))
        again = self._list()  # a new start reads the files, without the toolbox's own list (as a build does)
        self.assertTrue(again.tested("box:obs.set_scene"))
        self.assertEqual(again.note("box:obs.set_scene"), "the scene list / was slow once")
        self.assertEqual(again.changed("box:obs.set_scene"), "2026-10-09")
        self.assertFalse(again.tested("box:obs.mute"))

    def test_ai_checked_is_a_day_of_its_own_and_not_a_check(self) -> None:
        tested = self._list()
        tested.sync(ITEMS)
        tested.set_ai_checked("page:/variables")
        self.assertIn("| Variables | `/variables` | 2026-10-07 | - | - | - | - |  |", self._text("variables/page.md"))
        again = self._list()
        self.assertEqual(again.ai_checked("page:/variables"), "2026-10-07")
        self.assertFalse(again.tested("page:/variables"))
        self.assertEqual(again.changed("page:/variables"), "")
        again.sync(ITEMS)
        again.set_ai_checked("page:/variables", False)
        self.assertEqual(self._list().ai_checked("page:/variables"), "")
        with self.assertRaises(KeyError):
            again.set_ai_checked("box:not.there")

    def test_a_check_written_by_hand_counts(self) -> None:
        self._list().sync(ITEMS)
        file = self.folder / "connections" / "obs.md"
        file.write_text(file.read_text(encoding="utf-8").replace("| - | - | - | - | - |  |",
                                                                 "| - | Yes | yes | YES | 2026-10-08 | by hand |"),
                        encoding="utf-8")
        tested = self._list()
        self.assertTrue(tested.tested("connection:obs"))
        tested.sync(ITEMS)
        self.assertIn("| OBS | `obs` | - | yes | yes | yes | 2026-10-08 | by hand |", self._text("connections/obs.md"))

    def test_a_row_whose_thing_is_gone_stays_as_proof(self) -> None:
        tested = self._list()
        tested.sync(ITEMS)
        for check in ("works", "understandable", "usable"):
            tested.set_check("box:obs.mute", check, True)
        later = self._list()
        later.sync([item for item in ITEMS if item.id != "obs.mute"])
        self.assertEqual(self._text("flows/boxes/obs/audio.md").splitlines()[0], "# Flows > Boxes > OBS > Audio")
        self.assertIn("| Mute (not in the toolbox any more) | `obs.mute` | - | yes | yes | yes | 2026-10-07 |  |",
                      self._text("flows/boxes/obs/audio.md"))
        self.assertNotIn("audio", self._text("README.md"))  # it no longer counts
        self.assertIn("| **All** | **0** | **6** |", self._text("README.md"))
        once_more = self._list()
        once_more.sync([item for item in ITEMS if item.id != "obs.mute"])
        self.assertEqual(self._text("flows/boxes/obs/audio.md").count("not in the toolbox any more"), 1)

    def test_a_row_that_is_sorted_anew_moves_with_its_ticks(self) -> None:
        tested = self._list()
        tested.sync(ITEMS)
        tested.set_check("box:obs.mute", "works", True)
        moved = [replace(item, file="flows/boxes/obs/sound", heading="Flows > Boxes > OBS > Sound")
                 if item.id == "obs.mute" else item for item in ITEMS]
        self._list().sync(moved)
        self.assertNotIn("flows/boxes/obs/audio.md", self._files())
        self.assertIn("| Mute | `obs.mute` | - | yes | - | - | 2026-10-07 |  |",
                      self._text("flows/boxes/obs/sound.md"))

    def test_a_file_that_is_not_the_records_is_left_alone(self) -> None:
        self.folder.mkdir(parents=True)
        (self.folder / "notes.md").write_text("| a | `box.x` | - | yes | yes | yes | - |  |\n", encoding="utf-8")
        tested = self._list()
        tested.sync(ITEMS)
        self.assertFalse(tested.tested("box:box.x"))
        self.assertTrue((self.folder / "notes.md").is_file())

    def test_an_unknown_check_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self._list().set_check("box:x", "pretty", True)

    def test_nothing_is_tested_without_the_folder(self) -> None:
        self.assertFalse(self._list().tested("box:obs.set_scene"))

    def test_the_record_lives_in_the_projects_docs(self) -> None:
        self.assertEqual(TESTING_FOLDER, Path(__file__).resolve().parents[3] / "docs" / "tested")


if __name__ == "__main__":
    unittest.main()
