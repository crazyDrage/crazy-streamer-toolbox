import unittest

from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class TestFlowDraft(unittest.TestCase):
    def test_add_after_inserts_add_beside_runs_together_remove_bridges(self) -> None:
        d = FlowDraft("f", "F", nodes=[NodeDraft("n1", "a.x"), NodeDraft("n2", "a.y")],
                      wires=[FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")])
        new = d.add_after("n1", "done", "a.new", "done")
        self.assertEqual(new.id, "n3")
        self.assertEqual(set(d.wires), {FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n3"),
                                        FlowWire("n3", "done", "n2")})
        beside = d.add_beside("n2", "a.other")
        self.assertIn(FlowWire("n3", "done", beside.id), d.wires)
        d.remove("n3", ("done",))
        self.assertEqual(set(d.wires), {FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2"),
                                        FlowWire("n1", "done", "n4")})
        self.assertEqual(d.to_flow().targets("n1", "done"), ["n2", "n4"])

if __name__ == "__main__":
    unittest.main()
