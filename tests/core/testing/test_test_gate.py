import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.testing.test_gate import TestGate
from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS, TestList

ITEMS = [TestItem(BOX, "obs.set_scene", "Set scene", "OBS", file="flows/boxes/obs/general"),
         TestItem(BOX, "obs.mute", "Mute", "OBS", file="flows/boxes/obs/general"),
         TestItem(CONNECTION, "obs", "OBS", file="connections/obs")]


class TestTestGate(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "tested"
        self.actions = ActionRegistry()

        async def noop() -> None:
            return None

        for name in ("obs.set_scene", "obs.mute"):
            self.actions.add(name, noop)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_every_box_stays_and_carries_its_checks(self) -> None:
        tested = TestList(self.folder)
        tested.sync(ITEMS)
        for check in CHECKS:
            tested.set_check("box:obs.set_scene", check, True)
        TestGate(TestList(self.folder)).apply(self.actions, lambda: ITEMS)
        self.assertEqual([a.name for a in self.actions.all()], ["obs.mute", "obs.set_scene"])
        self.assertTrue(self.actions.get("obs.set_scene").is_tested)
        self.assertFalse(self.actions.get("obs.mute").is_tested)

    def test_it_writes_no_files(self) -> None:
        gate = TestGate(TestList(self.folder))
        gate.apply(self.actions, lambda: ITEMS)
        self.assertFalse(self.folder.exists())  # the files are made by devtools/tested
        self.assertEqual(gate.items(), ITEMS)
        gate.tested.set_check("box:obs.mute", "works", True)  # a tick still finds its file
        self.assertIn("| Mute | `obs.mute` | - | yes |",
                      (self.folder / "flows" / "boxes" / "obs" / "general.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
