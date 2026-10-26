import unittest

from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.old_end_boxes import end_boxes_from_lines


class TestOldEndBoxes(unittest.TestCase):
    """End boxes had names (a way out each; round 53 a run dot per name); since round 55 only values."""

    def test_the_names_go_and_the_values_stay(self) -> None:
        nodes, wires = end_boxes_from_lines((FlowNode("e", "logic.end", {"name": "found", "count": "3"}),
                                             FlowNode("o", "logic.output", {"name": "not an end"})),
                                            (FlowWire("start", "out", "e"),))
        self.assertEqual([n.params for n in nodes], [{"count": "3"}, {"name": "not an end"}])
        self.assertEqual(wires, (FlowWire("start", "out", "e"),))

    def test_the_wires_into_a_names_run_dot_go_into_the_run_dot(self) -> None:
        nodes, wires = end_boxes_from_lines(
            (FlowNode("end", "logic.end", {"names": 2, "name_1": "big", "name_2": "small"}, box=(10, 20)),),
            (FlowWire("ask", "then", "end", "name_1"), FlowWire("ask", "else", "end", "name_2"),
             FlowWire("x", "done", "end", "name_1"), FlowWire("x", "done", "end")))
        self.assertEqual([(n.id, n.params, n.box) for n in nodes], [("end", {}, (10, 20))])
        self.assertEqual(wires, (FlowWire("ask", "then", "end"), FlowWire("ask", "else", "end"),
                                 FlowWire("x", "done", "end")))

    def test_a_flow_file_is_changed_when_it_is_read(self) -> None:
        flow = FlowStore.parse("f", {"nodes": [{"id": "e", "action": "logic.end", "params": {"name_1": "found"}}]})
        self.assertEqual(flow.nodes[0].params, {})


if __name__ == "__main__":
    unittest.main()
