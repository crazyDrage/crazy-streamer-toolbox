import unittest

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.variable_renamer import VariableRenamer


class TestVariableRenamer(unittest.TestCase):
    def test_every_place_a_flow_can_use_the_variable(self) -> None:
        flow = Flow("f", "F", (
            FlowNode("n1", "vts.move_model_to", {"position": "${var.pos}"}),
            FlowNode("n2", "logic.if", {"left": "${var.pos.x}", "right": "${var.pos_old}"}),  # pos_old: another
            FlowNode("n3", "a.say", {"text": "at ${var.pos.x} and ${var.pos.y}"}),
            FlowNode("n4", "vts.get_model_position", save_as="pos"),
            FlowNode("n5", "var.set", {"name": "pos", "value": 1}),
            FlowNode("n6", "logic.for_each", {"items": "${var.list}", "item": "pos"}),
            FlowNode("n7", "a.say", {"text": "pos stays text"}),
            FlowNode("n8", "logic.value", {"values": {"where": "${var.pos.x}"}}),
            FlowNode("n9", "var.get", {"name": "pos"}),
        ))
        renamed = VariableRenamer("pos", "dragon_spot").flow(flow)
        params = {n.id: n.params for n in renamed.nodes}
        self.assertEqual(params["n1"]["position"], "${var.dragon_spot}")
        self.assertEqual(params["n2"], {"left": "${var.dragon_spot.x}", "right": "${var.pos_old}"})
        self.assertEqual(params["n3"]["text"], "at ${var.dragon_spot.x} and ${var.dragon_spot.y}")
        self.assertEqual(renamed.node("n4").save_as, "dragon_spot")
        self.assertEqual((params["n5"]["name"], params["n6"]["item"]), ("dragon_spot", "dragon_spot"))
        self.assertEqual((params["n8"], params["n9"]), ({"values": {"where": "${var.dragon_spot.x}"}},
                                                        {"name": "dragon_spot"}))
        self.assertEqual(params["n7"]["text"], "pos stays text")

    def test_a_flow_without_it_is_left_alone(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "var.set", {"name": "other", "value": "${var.posx}"}),))
        self.assertIsNone(VariableRenamer("pos", "spot").flow(flow))
