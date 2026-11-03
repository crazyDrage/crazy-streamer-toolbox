import unittest

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft


class TestFlowDraftStartBoxes(unittest.TestCase):
    """His round 63: triggers are Start boxes of the flow, a new flow has its End box."""

    def test_a_new_flow_starts_with_start_wired_to_end(self) -> None:
        d = FlowDraft.new()
        self.assertEqual(([n.id for n in d.nodes], d.wires), (["end"], [FlowWire("start", "out", "end")]))

    def test_a_trigger_added_is_wired_like_start_and_taken_away_with_its_wires(self) -> None:
        d = FlowDraft.new()
        trigger = d.add_trigger(FlowTrigger("twitch.redeem", {"reward": "Hydrate!"}))
        self.assertEqual(trigger.id, "t1")
        self.assertIn(FlowWire("t1", "out", "end"), d.wires)
        d.set_trigger("t1", match={"reward": "Lizard"}, box=(20, 160))
        self.assertEqual((d.trigger("t1").match, d.trigger("t1").box), ({"reward": "Lizard"}, (20, 160)))
        d.nodes[0].params["note"] = "${box.t1.user}"
        d.remove_trigger("t1")
        flow = d.to_flow()
        self.assertEqual((flow.triggers, flow.wires), ((), (FlowWire("start", "out", "end"),)))
        self.assertEqual(flow.node("end").params["note"], "${box}")  # its dot is gone: waits for a new wire

    def test_a_box_added_after_start_goes_after_the_starts_wired_the_same(self) -> None:
        d = FlowDraft.new()
        d.add_trigger(FlowTrigger("twitch.redeem"))
        d.add_trigger(FlowTrigger("twitch.chat"))
        d.wires = [w for w in d.wires if w.source != "t2"] + [FlowWire("t2", "out", "end", "")]
        d.wires.append(FlowWire("t2", "out", "n9"))  # t2 leads somewhere else as well: it stays
        node = d.add_after("t1", "out", "a.sound", "done")
        self.assertEqual(set(d.wires), {FlowWire("start", "out", node.id), FlowWire("t1", "out", node.id),
                                        FlowWire(node.id, "done", "end"), FlowWire("t2", "out", "end"),
                                        FlowWire("t2", "out", "n9")})

    def test_a_flow_made_in_code_gets_its_start_boxes_in_the_editor(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "a.x", {"who": "${box.start.user}"}),),
                    (FlowWire("start", "out", "n1"),), (FlowTrigger("twitch.redeem", {"reward": "Lizard"}),))
        d = FlowDraft.from_flow(flow)
        self.assertEqual([t.id for t in d.triggers], ["t1"])
        self.assertIn(FlowWire("t1", "out", "n1"), d.wires)
        self.assertEqual(d.node("n1").params["who"], "${box.t1.user}")


if __name__ == "__main__":
    unittest.main()
