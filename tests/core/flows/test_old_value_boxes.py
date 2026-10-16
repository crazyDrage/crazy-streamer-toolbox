import unittest

from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.old_value_boxes import lines_from_old_values


class TestOldValueBoxes(unittest.TestCase):
    def test_the_one_value_becomes_a_line_and_its_wires_follow(self) -> None:
        nodes = lines_from_old_values((
            FlowNode("v", "logic.value", {"value": "Hex"}),
            FlowNode("v1", "logic.value", {"value": 5}),  # an id that starts like the other one
            FlowNode("a", "a.say", {"text": "${box.v}", "n": "${box.v1}", "x": "${box.v.x}", "both": "${box.v} + 1"}),
            FlowNode("new", "logic.value", {"values": {"value": "already lines"}}),
            FlowNode("b", "a.say", {"text": "${box.new.value}"}),
        ))
        params = {n.id: n.params for n in nodes}
        self.assertEqual(params["v"], {"values": {"value": "Hex"}})
        self.assertEqual(params["v1"], {"values": {"value": 5}})
        self.assertEqual(params["a"], {"text": "${box.v.value}", "n": "${box.v1.value}", "x": "${box.v.value.x}",
                                       "both": "${box.v.value} + 1"})
        self.assertEqual(params["b"], {"text": "${box.new.value}"})
        self.assertEqual(params["new"], {"values": {"value": "already lines"}})

    def test_a_flow_file_is_changed_when_it_is_read(self) -> None:
        flow = FlowStore.parse("f", {"nodes": [{"id": "v", "action": "logic.value", "params": {"value": "Hex"}},
                                               {"id": "a", "action": "a.say", "params": {"text": "${box.v}"}}]})
        self.assertEqual([n.params for n in flow.nodes], [{"values": {"value": "Hex"}}, {"text": "${box.v.value}"}])
