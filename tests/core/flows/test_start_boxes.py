import unittest

from streamer_toolbox.core.flows.flow import END_ACTION, Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.old_start_box import start_boxes_from_triggers
from streamer_toolbox.core.flows.start_boxes import new_flow, with_trigger


class TestStartBoxes(unittest.TestCase):
    """His round 63: a Start box per trigger, the inputs on the Input box, a new flow comes with its End box."""

    def test_a_new_flow_has_start_wired_to_end_and_each_trigger_too(self) -> None:
        flow = new_flow("hydrate", "Hydrate", triggers=(FlowTrigger("twitch.redeem", {"reward": "Hydrate!"}),
                                                        FlowTrigger("youtube.chat", {"command": "!hydrate"})),
                        folder="Redeems")
        self.assertEqual([n.action for n in flow.nodes], [END_ACTION])
        self.assertEqual([t.id for t in flow.triggers], ["t1", "t2"])
        self.assertEqual(flow.wires, (FlowWire("start", "out", "end"), FlowWire("t1", "out", "end"),
                                      FlowWire("t2", "out", "end")))
        self.assertEqual((flow.folder, flow.starts()), ("Redeems", ["start", "t1", "t2"]))

    def test_an_added_trigger_starts_what_start_starts(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "a.x"), FlowNode("n2", "a.x")),
                    (FlowWire("start", "out", "n1"), FlowWire("start", "out", "n2", "stop")),
                    (FlowTrigger("timer", {"every": 5}, "t1"),))
        flow = with_trigger(flow, FlowTrigger("twitch.chat", {"command": "!go"}))
        self.assertEqual(flow.trigger("t2").match, {"command": "!go"})
        self.assertEqual(flow.wires[-2:], (FlowWire("t2", "out", "n1"), FlowWire("t2", "out", "n2", "stop")))
        self.assertEqual(flow.without_triggers().wires, flow.wires[:2])

    def test_an_older_file_gets_a_start_box_per_trigger_and_its_wires_move(self) -> None:
        nodes = (FlowNode("n1", "a.x", {"who": "${box.start.user}", "text": "hi ${box.start.message}!",
                                        "secs": "${box.start.seconds}", "list": ["${box.start.reward}"]}),)
        wires = (FlowWire("start", "out", "n1"),)
        triggers = (FlowTrigger("twitch.redeem", {"reward": "Lizard"}), FlowTrigger("twitch.chat", {}))
        nodes, wires, triggers = start_boxes_from_triggers(nodes, wires, triggers, (FlowInput("seconds"),))
        self.assertEqual([t.id for t in triggers], ["t1", "t2"])
        self.assertEqual(wires, (FlowWire("start", "out", "n1"), FlowWire("t1", "out", "n1"),
                                 FlowWire("t2", "out", "n1")))
        # an input reads the Input box; a field reads the first trigger that gives it (message: the chat)
        self.assertEqual(nodes[0].params, {"who": "${box.t1.user}", "text": "hi ${box.t2.message}!",
                                           "secs": "${box.input.seconds}", "list": ["${box.t1.reward}"]})
        again = start_boxes_from_triggers(nodes, wires, triggers, (FlowInput("seconds"),))
        self.assertEqual(again, (nodes, wires, triggers))  # read again: nothing changes
