import unittest

from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import DrawflowGraph
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class TestDrawflowGraphDataOnly(unittest.TestCase):
    """His round 52: Get variable (and Value) need no run wire, so they have none."""

    def setUp(self) -> None:
        self.graph = DrawflowGraph(lambda action, params: ("done",), lambda a: a,
                                   data_outputs_of=lambda node: [("", "result")],
                                   data_only_of=lambda node: node.action == "var.get")

    def test_its_run_dots_are_hidden_and_a_run_wire_to_or_from_it_goes(self) -> None:
        draft = FlowDraft("f", "F", nodes=[NodeDraft("g", "var.get", {"name": "count"}), NodeDraft("n2", "a.say")],
                          wires=[FlowWire("start", "out", "g"), FlowWire("g", "done", "n2"),
                                 FlowWire("start", "out", "n2")])
        data = self.graph.build(draft)
        self.assertIn("tb-data-only", data["drawflow"]["Home"]["data"]["2"]["class"])
        self.assertNotIn("tb-data-only", self.graph.css(draft.node("n2")))
        self.graph.read(data, draft)
        self.assertEqual(draft.wires, [FlowWire("start", "out", "n2")])


if __name__ == "__main__":
    unittest.main()
