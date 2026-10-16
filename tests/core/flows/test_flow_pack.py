import unittest

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.flows.flow_wire import FlowWire


class FlowPackTest(unittest.TestCase):
    def setUp(self) -> None:
        wires = (FlowWire("start", "out", "n1"),)
        self.pack = FlowPack("lizard", (
            Flow("add", "Add", (FlowNode("n1", "text.join", {"a": "x"}),), wires, folder="lizard"),
            Flow("plus", "Plus", (FlowNode("n1", "flow.add"), FlowNode("n2", "flow.sound")), wires, folder="lizard")))

    def test_text_and_back(self) -> None:
        again = FlowPack.from_text(self.pack.to_text())
        self.assertEqual((again.folder, again.flows), ("lizard", self.pack.flows))

    def test_needs_names_the_flows_that_are_not_in_it(self) -> None:
        self.assertEqual(self.pack.needs(), ["sound"])

    def test_renamed_takes_the_boxes_along(self) -> None:
        renamed = self.pack.renamed({"add": "add_2", "plus": "plus"})
        self.assertEqual([f.name for f in renamed.flows], ["add_2", "plus"])
        self.assertEqual([n.action for n in renamed.flows[1].nodes], ["flow.add_2", "flow.sound"])
