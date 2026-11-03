import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.system.program_actions import ProgramActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.box_dots import BoxDots
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class TestBoxOutputNames(unittest.TestCase):
    """His idea of 10-30: Run Python's outputs are names he types; each one is a dot of the box."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        actions = ActionRegistry()
        ProgramActions(Path(self._dir.name) / "python").add_to(actions)
        runner = FlowRunner(actions, VariableStore(Path(self._dir.name) / "variables"))
        self.draft = FlowDraft("f", "F", nodes=[
            NodeDraft("n1", "system.python", {"file": "lizard", "outputs": "text, count", "name": "${box.n2}"})])
        self.dots = BoxDots(actions, runner, self.draft)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_dot_per_name_and_the_inputs_on_the_left(self) -> None:
        box = self.draft.node("n1")
        self.assertEqual([("", "result"), ("printed", "printed · text"), ("text", "text"), ("count", "count")],
                         self.dots.data_outputs(box))
        self.assertIn("name", self.dots.data_inputs(box))

    def test_the_dots_follow_the_names(self) -> None:
        box = self.draft.node("n1")
        box.params["outputs"] = "count"
        self.assertEqual({"count": ""}, self.dots.own_outputs(box))
        box.params["outputs"] = ""
        self.assertEqual({}, self.dots.own_outputs(box))


if __name__ == "__main__":
    unittest.main()
