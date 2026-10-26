import unittest

from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import DrawflowGraph
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft

LINES = ["value_1", "value_2"]


def _lines(node: NodeDraft) -> list[str]:
    return LINES if node.action == "logic.choose" else []


class TestDrawflowGraphLines(unittest.TestCase):
    """His round 54: Choose value's dots come in pairs, each line's run dot above its value's."""

    def setUp(self) -> None:
        self.graph = DrawflowGraph(lambda action, params: ("done",), lambda a: a, entries_of=_lines,
                                   data_inputs_of=lambda node: LINES if _lines(node) else [],
                                   lines_of=_lines)
        self.draft = FlowDraft("f", "F", nodes=[NodeDraft("c", "logic.choose", {"value_1": "a", "value_2": "b"})],
                               wires=[FlowWire("start", "out", "c", "value_2")])

    def test_the_dots_are_shown_line_by_line(self) -> None:
        box = self.graph.build(self.draft)["drawflow"]["Home"]["data"]["2"]
        # input_1 (hidden), value_1's run dot (2) and value (4), value_2's (3, 5)
        self.assertEqual(box["data"]["order_in"], [1, 2, 4, 3, 5])
        rows = box["html"].split('class="tb-in')[1:]
        self.assertEqual([row.split(">", 1)[1].split("<", 1)[0] for row in rows],
                         ["value 1", "value 1", "value 2", "value 2"])

    def test_the_wires_are_read_back_by_number_not_by_where_they_are_shown(self) -> None:
        data = self.graph.build(self.draft)
        self.graph.read(data, self.draft)
        self.assertEqual(self.draft.wires, [FlowWire("start", "out", "c", "value_2")])

    def test_a_box_without_lines_keeps_its_order(self) -> None:
        draft = FlowDraft("f", "F", nodes=[NodeDraft("n", "a.say", {})])
        self.assertEqual(self.graph.build(draft)["drawflow"]["Home"]["data"]["2"]["data"]["order_in"], [])


if __name__ == "__main__":
    unittest.main()
