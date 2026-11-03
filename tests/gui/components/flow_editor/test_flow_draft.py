import unittest

from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


class TestFlowDraft(unittest.TestCase):
    def test_empty_lines_stay_on_save_empty_fields_go(self) -> None:
        """His round 81 (7 b): Get settings' lines stay even when empty; an empty field of its own still goes."""
        node = NodeDraft("n7", "obs.set_source_settings", {"source": "so-event", "settings": "", "url": "",
                                                           "width": ""})
        d = FlowDraft("f", "F", nodes=[node])
        self.assertEqual(d.to_flow().nodes[0].params, {"source": "so-event"})
        d.named_lines = lambda n: ["url", "width"]
        self.assertEqual(d.to_flow().nodes[0].params, {"source": "so-event", "url": "", "width": ""})

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

    def test_a_flow_takes_one_box_that_is_once_per_flow(self) -> None:
        async def end(**values):
            return values

        end_box = RegisteredAction("logic.end", end, "", "End", named_lines=True, once_per_flow=True)
        other = RegisteredAction("a.x", end, "")
        d = FlowDraft("f", "F", nodes=[NodeDraft("n1", "a.x")])
        self.assertEqual(d.refuses(end_box), "")
        d.new_node("logic.end")
        self.assertIn("has its End box already: give it more values", d.refuses(end_box))
        self.assertEqual((d.refuses(other), d.refuses(None)), ("", ""))


if __name__ == "__main__":
    unittest.main()
