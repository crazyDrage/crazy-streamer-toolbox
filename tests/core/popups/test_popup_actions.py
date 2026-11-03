import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.popups.boxes.ask_yes_no import AskYesNo
from streamer_toolbox.core.popups.boxes.show_message import ShowMessage
from streamer_toolbox.core.popups.popup_actions import PopupActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from tests.fakes.fake_confirm_service import FakeConfirmService
from tests.fakes.fake_message_service import FakeMessageService


class TestPopupActions(unittest.IsolatedAsyncioTestCase):
    async def test_message_and_answers(self) -> None:
        messages = FakeMessageService()
        self.assertEqual(await ShowMessage(messages, FakeConfirmService(True)).run("clip done", "Raid"), 1)
        self.assertEqual(messages.shown, [("clip done", "Raid")])
        self.assertEqual(await AskYesNo(messages, FakeConfirmService(True)).run("Raid xyz?"), "yes")
        self.assertEqual(await AskYesNo(messages, FakeConfirmService(False)).run("?"), "no")
        self.assertEqual(await AskYesNo(messages, FakeConfirmService(None)).run("?"), "no_answer")

    async def test_the_answer_picks_the_way_on_in_a_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            actions = ActionRegistry()
            confirm = FakeConfirmService(None)
            PopupActions(FakeMessageService(), confirm).add_to(actions)
            ran = []

            async def mark(way: str) -> None:
                ran.append(way)

            actions.add("t.mark", mark)
            nodes = (FlowNode("ask", "popup.ask", {"question": "Raid?", "seconds": "5"}),
                     FlowNode("y", "t.mark", {"way": "yes"}), FlowNode("n", "t.mark", {"way": "no"}),
                     FlowNode("x", "t.mark", {"way": "no_answer"}))
            wires = (FlowWire("start", "out", "ask"), FlowWire("ask", "yes", "y"), FlowWire("ask", "no", "n"),
                     FlowWire("ask", "no_answer", "x"))
            await FlowRunner(actions, VariableStore(Path(tmp) / "v.json")).run(Flow("f", "F", nodes, wires))
            self.assertEqual(ran, ["no_answer"])
            self.assertEqual(confirm.asked, [("Raid?", 5.0)])


if __name__ == "__main__":
    unittest.main()
