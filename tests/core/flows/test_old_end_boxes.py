import unittest

from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.old_end_boxes import end_lines_from_old_names


class TestOldEndBoxes(unittest.TestCase):
    def test_the_one_name_becomes_line_one(self) -> None:
        nodes = end_lines_from_old_names((FlowNode("e", "logic.end", {"name": "found"}),
                                          FlowNode("lines", "logic.end", {"name_1": "a", "name_2": "b"}),
                                          FlowNode("o", "logic.output", {"name": "kept"})))
        self.assertEqual([n.params for n in nodes], [{"name_1": "found"}, {"name_1": "a", "name_2": "b"},
                                                     {"name": "kept"}])

    def test_a_flow_file_is_changed_when_it_is_read(self) -> None:
        flow = FlowStore.parse("f", {"nodes": [{"id": "e", "action": "logic.end", "params": {"name": "found"}}]})
        self.assertEqual(flow.nodes[0].params, {"name_1": "found"})
        self.assertEqual(flow.ends, ("found",))
