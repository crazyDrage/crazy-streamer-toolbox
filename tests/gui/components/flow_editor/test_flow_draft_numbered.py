import unittest

from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class TestFlowDraftNumbered(unittest.TestCase):
    def _draft(self) -> FlowDraft:
        switch = NodeDraft("sw", "logic.switch", {"value": "x", "cases": 3, "case_1": "a", "case_3": "c"})
        wires = [FlowWire("start", "out", "sw"), FlowWire("sw", "case_1", "n1"), FlowWire("sw", "case_2", "n2"),
                 FlowWire("sw", "case_3", "n3"), FlowWire("sw", "else", "n4")]
        return FlowDraft("f", "F", nodes=[switch, *(NodeDraft(f"n{i}", "a.mark") for i in range(1, 5))], wires=wires)

    def test_taking_a_case_away_moves_the_later_ones_up_with_their_wires(self) -> None:
        draft = self._draft()
        draft.remove_numbered("sw", "case", 2)
        self.assertEqual(draft.node("sw").params, {"value": "x", "cases": 2, "case_1": "a", "case_2": "c"})
        self.assertEqual(draft.wires, [FlowWire("start", "out", "sw"), FlowWire("sw", "case_1", "n1"),
                                       FlowWire("sw", "case_2", "n3"), FlowWire("sw", "else", "n4")])

    def test_the_last_case_stays(self) -> None:
        draft = self._draft()
        for _ in range(3):
            draft.remove_numbered("sw", "case", 1)
        self.assertEqual(draft.node("sw").params, {"value": "x", "cases": 1, "case_1": "c"})
        self.assertEqual([w.port for w in draft.wires if w.source == "sw"], ["case_1", "else"])

    def test_an_empty_case_is_kept_by_its_count_when_saved(self) -> None:
        flow = self._draft().to_flow()
        self.assertEqual(flow.node("sw").params, {"value": "x", "cases": 3, "case_1": "a", "case_3": "c"})


if __name__ == "__main__":
    unittest.main()

    def test_wires_follow_a_renamed_value_line_and_wait_when_it_is_taken_away(self) -> None:
        draft = FlowDraft("f", "F", nodes=[
            NodeDraft("v", "logic.value", {"values": {"power": 10, "model": "Hex"}}),
            NodeDraft("a", "a.say", {"p": "${box.v.power}", "q": "${box.v.power.@count}", "m": "${box.v.model}",
                                     "other": "${box.v2.power}"})])
        draft.rename_output("v", "power", "strength")
        self.assertEqual(draft.node("a").params, {"p": "${box.v.strength}", "q": "${box.v.strength.@count}",
                                                  "m": "${box.v.model}", "other": "${box.v2.power}"})
        draft.rename_output("v", "model", "")
        self.assertEqual(draft.node("a").params["m"], "${box}")

    def test_a_box_that_only_gives_values_is_taken_out_of_the_run_chain(self) -> None:
        draft = FlowDraft("f", "F", nodes=[NodeDraft("g", "var.get"), NodeDraft("a", "a.x"), NodeDraft("b", "a.y")],
                          wires=[FlowWire("start", "out", "g"), FlowWire("g", "done", "a"), FlowWire("g", "done", "b")])
        draft.take_off_run_wires("g")
        self.assertEqual(draft.wires, [FlowWire("start", "out", "a"), FlowWire("start", "out", "b")])
