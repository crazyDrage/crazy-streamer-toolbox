import unittest

from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.old_split_boxes import split_boxes_away


class TestOldSplitBoxes(unittest.TestCase):
    def test_the_fields_are_wired_from_what_it_took_apart_and_the_box_goes(self) -> None:
        # his Play video flow: Video info → Split data → Set source size / Wait
        nodes, wires = split_boxes_away((
            FlowNode("n1", "video.info", {"path": "${box.start.path}"}),
            FlowNode("n2", "data.split", {"data": "${box.n1}", "fields": {"width": "number", "seconds": "number"}}),
            FlowNode("n3", "a.size", {"width": "${box.n2.width}", "said": "${box.n2.seconds} s", "all": "${box.n2}"}),
            FlowNode("v", "data.split", {"data": "${var.pos}", "fields": {"x": "number"}}),
            FlowNode("n4", "a.move", {"x": "${box.v.x.@count}"}),
            FlowNode("n5", "data.split", {"data": "${box.n2}", "fields": {"width": "number"}}),  # Split after Split
            FlowNode("n6", "a.size", {"width": "${box.n5.width}"}),
            FlowNode("text", "data.split", {"data": '{"x": 1}'}),  # not one ${...}: stays
        ), (FlowWire("start", "out", "n1"),))
        params = {n.id: n.params for n in nodes}
        self.assertEqual(list(params), ["n1", "n3", "n4", "n6", "text"])
        self.assertEqual(params["n3"], {"width": "${box.n1.width}", "said": "${box.n1.seconds} s", "all": "${box.n1}"})
        self.assertEqual(params["n4"], {"x": "${var.pos.x.@count}"})
        self.assertEqual(params["n6"], {"width": "${box.n1.width}"})
        self.assertEqual(wires, (FlowWire("start", "out", "n1"),))

    def test_a_run_wire_through_it_is_bridged(self) -> None:
        nodes, wires = split_boxes_away(
            (FlowNode("a", "a.get"), FlowNode("s", "data.split", {"data": "${box.a}"}), FlowNode("b", "a.use")),
            (FlowWire("start", "out", "a"), FlowWire("a", "done", "s"), FlowWire("s", "done", "b")))
        self.assertEqual([n.id for n in nodes], ["a", "b"])
        self.assertEqual(wires, (FlowWire("start", "out", "a"), FlowWire("a", "done", "b")))
