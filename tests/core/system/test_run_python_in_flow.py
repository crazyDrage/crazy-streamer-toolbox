import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.system.program_actions import ProgramActions
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestRunPythonInFlow(unittest.IsolatedAsyncioTestCase):
    """A Start's value wired into an input, an output wired into the next box."""

    async def test_wires_in_and_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "python"
            folder.mkdir()
            (folder / "double.py").write_text("def run(number=None):\n    return {'twice': number * 2}\n",
                                              encoding="utf-8")
            actions = ActionRegistry()
            variables = VariableStore(Path(tmp) / "variables")
            LogicActions(variables).add_to(actions)
            ProgramActions(folder).add_to(actions)
            flow = Flow("f", "F", (
                FlowNode("n1", "system.python", {"file": "double", "outputs": "twice", "number": 21}),
                FlowNode("n2", "var.set", {"name": "answer", "value": "${box.n1.twice}"})),
                wires=(FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
            await FlowRunner(actions, variables).run(flow)
            self.assertEqual(42, variables.get("answer"))


if __name__ == "__main__":
    unittest.main()
