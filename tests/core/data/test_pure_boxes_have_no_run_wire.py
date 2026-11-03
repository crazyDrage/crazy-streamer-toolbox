import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.json_actions import JsonActions
from streamer_toolbox.core.data.list_actions import ListActions
from streamer_toolbox.core.data.object_actions import ObjectActions
from streamer_toolbox.core.data.text_actions import TextActions
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore

# what has to keep its run wire: changes a variable, branches (then / else), or is random (two readers would get
# different picks)
KEEP_RUN_WIRE = {"list.add", "list.remove", "list.contains", "object.has", "list.random", "list.shuffle"}


class TestPureBoxesHaveNoRunWire(unittest.IsolatedAsyncioTestCase):
    """His rule (round 62 A, notes of 10-29: "does Text · Replace in text need a trigger connection?"): only the
    toolbox's own values and pure calculations go without a run wire."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self._dir.name) / "variables.json")
        self.actions = ActionRegistry()
        for group in (TextActions(), JsonActions(), ObjectActions(), ListActions(self.variables)):
            group.add_to(self.actions)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_text_list_object_and_json_boxes_only_give_values(self) -> None:
        names = {a.name for a in self.actions.all(include_flow_only=True)}
        self.assertTrue(KEEP_RUN_WIRE <= names, KEEP_RUN_WIRE - names)
        with_wire = sorted(a.name for a in self.actions.all(include_flow_only=True) if not a.data_only)
        self.assertEqual(with_wire, sorted(KEEP_RUN_WIRE))

    async def test_build_text_puts_its_named_values_into_the_text(self) -> None:
        """His notes of 10-29: "{name} just gave {amount} Bits." with values added like the End box's."""
        box = self.actions.get("text.build")
        self.assertTrue(box.named_lines and box.data_only)
        said = await self.actions.run("text.build", text="{name} just gave {amount} Bits.", name="Kit", amount=100)
        self.assertEqual(said, "Kit just gave 100 Bits.")
        self.assertEqual(await self.actions.run("text.build", text="{name}!"), "{name}!")  # no such value: stays

    async def test_a_flow_saved_with_a_run_wire_through_one_still_goes_on(self) -> None:
        """His flows from before: start → Replace in text → record. The record box still runs, with the value."""
        seen = []

        async def record(text: str = "") -> None:
            seen.append(text)

        self.actions.add("t.record", record)
        replace = "text.replace"
        flow = Flow("f", "F", (FlowNode("n1", replace, {"text": "hi Kit", "find": "Kit", "replace_with": "Vex"}),
                               FlowNode("n2", "t.record", {"text": "${box.n1}"})),
                    (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        runner = FlowRunner(self.actions, self.variables)
        runner.register(flow)
        await self.actions.run("flow.f")
        self.assertEqual(seen, ["hi Vex"])


if __name__ == "__main__":
    unittest.main()
