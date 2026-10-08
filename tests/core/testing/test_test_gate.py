import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.left_out import leave_out, left_out, left_out_connections
from streamer_toolbox.core.testing.test_gate import TestGate
from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, PAGE, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS, TestList

ITEMS = [TestItem(BOX, "obs.set_scene", "Set scene", "OBS", file="flows/boxes/obs/general"),
         TestItem(BOX, "obs.mute", "Mute", "OBS", file="flows/boxes/obs/general"),
         TestItem(CONNECTION, "obs", "OBS", file="connections/obs"),
         TestItem(CONNECTION, "rumble", "Rumble", file="connections/rumble"),
         TestItem(TOOL, "points", "Points", file="tools/points"),
         TestItem(TOOL, "sammi_decks", "SAMMI decks", file="tools/sammi_decks"),
         TestItem(TRIGGER, "timer", "Timer", "Toolbox", file="flows/triggers/toolbox"),
         TestItem(TRIGGER, "obs.scene_changed", "Scene changed", "OBS", file="flows/triggers/obs"),
         TestItem(PAGE, "/variables", "Variables", "Variables", file="variables/page"),
         TestItem(PAGE, "/overlays?show=alerts", "Alerts", "Overlay", file="overlay/page")]
TESTED = ("box:obs.set_scene", "connection:obs", "tool:points", "trigger:timer", "page:/variables")


class TestTestGate(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "tested"
        self.addCleanup(leave_out, ())
        self.actions = ActionRegistry()

        async def noop() -> None:
            return None

        for name in ("obs.set_scene", "obs.mute", "vts.pin_item"):
            self.actions.add(name, noop)
        self.tools = [("toolbox", "Points", "toll", "", noop), ("sammi_decks", "SAMMI decks", "", "", noop)]

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _record(self) -> TestList:
        tested = TestList(self.folder)
        tested.sync(ITEMS)
        for key in TESTED:
            for check in CHECKS:
                tested.set_check(key, check, True)
        return TestList(self.folder)

    def test_a_build_offers_only_what_is_tested(self) -> None:
        gate = TestGate(self._record(), True, parked=["vts.pin_item"])
        self.assertTrue(gate.keeps("obs"))
        self.assertFalse(gate.keeps("rumble"))
        gate.apply(self.actions, self.tools, lambda: ITEMS)
        self.assertEqual([a.name for a in self.actions.all()], ["obs.set_scene"])
        self.assertEqual([tool[1] for tool in self.tools], ["Points"])
        self.assertIn("rumble", left_out_connections())
        self.assertTrue(left_out("obs.scene_changed"))
        self.assertFalse(left_out("timer"))
        self.assertEqual(gate.untested_pages, {"/overlays?show=alerts"})

    def test_the_project_folder_offers_everything_and_writes_no_files(self) -> None:
        gate = TestGate(TestList(self.folder), False, parked=["vts.pin_item"])
        self.actions.park(["vts.pin_item"])
        self.assertTrue(gate.keeps("rumble"))
        gate.apply(self.actions, self.tools, lambda: ITEMS)
        self.assertEqual([a.name for a in self.actions.all()], ["obs.mute", "obs.set_scene"])
        self.assertEqual(len(self.tools), 2)
        self.assertEqual(left_out_connections(), frozenset())
        self.assertEqual(gate.untested_pages, set())
        self.assertFalse(self.folder.exists())  # the files are made by devtools/tested
        self.assertEqual(gate.items(), ITEMS)
        gate.tested.set_check("box:obs.mute", "works", True)  # a tick still finds its file
        self.assertIn("| Mute | `obs.mute` | - | yes |",
                      (self.folder / "flows" / "boxes" / "obs" / "general.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
