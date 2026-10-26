import os
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowLibraryReload(unittest.TestCase):
    """His round 63: a flow file changed outside the toolbox is taken in without a restart."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.flows = folder / "flows"
        self.actions = ActionRegistry()
        self.library = FlowLibrary(FlowStore(self.flows), FlowStore(folder / "t"),
                                   FlowRunner(self.actions, VariableStore(folder / "v.json")), self.actions)
        self.library.save(Flow("kept", "Kept"))
        self.library.save(Flow("gone", "Gone"))
        self.library.load()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, name: str, text: str) -> None:
        path = self.flows / f"{name}.toml"
        path.write_text(text, encoding="utf-8")
        later = path.stat().st_mtime_ns + 10 ** 9  # a clock that ticks coarsely still sees it changed
        os.utime(path, ns=(later, later))

    def test_new_changed_and_deleted_files(self) -> None:
        self.assertEqual(self.library.reload(), [])  # nothing changed
        self._write("new", 'label = "New one"\nnodes = []\n')
        self._write("kept", 'label = "Kept, edited by hand"\nnodes = []\n')
        (self.flows / "gone.toml").unlink()
        self.assertEqual(sorted(self.library.reload()), ["gone", "kept", "new"])
        self.assertEqual([f.label for f in self.library.all()], ["Kept, edited by hand", "New one"])
        self.assertIn("flow.new", self.actions)
        self.assertNotIn("flow.gone", self.actions)

    def test_a_broken_file_keeps_the_flow_as_it_was(self) -> None:
        self._write("kept", "label = ")
        with self.assertLogs(level="ERROR"):
            self.assertEqual(self.library.reload(), [])
        self.assertEqual(self.library.get("kept").label, "Kept")

    def test_a_flow_saved_in_the_toolbox_isnt_read_again(self) -> None:
        self.library.save(Flow("kept", "Kept again"))
        self.assertEqual(self.library.reload(), [])


if __name__ == "__main__":
    unittest.main()
