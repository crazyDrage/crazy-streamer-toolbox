import unittest

from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import DrawflowGraph
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


def ports(action: str, params: dict) -> tuple[str, ...]:
    return ("then", "else") if action == "logic.if" else ("done",)


def draft() -> FlowDraft:
    return FlowDraft("f", "F", nodes=[NodeDraft("n1", "logic.if"), NodeDraft("n2", "a.x"), NodeDraft("n3", "a.y"),
                                      NodeDraft("n4", "a.z", enabled=False)],
                     wires=[FlowWire("start", "out", "n1"), FlowWire("n1", "then", "n2"),
                            FlowWire("n1", "then", "n3"), FlowWire("n1", "else", "n4")])


class TestDrawflowGraph(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = DrawflowGraph(ports, lambda a: a.upper())

    def test_round_trip_keeps_wires_ports_and_places_boxes_by_depth(self) -> None:
        d = draft()
        data = self.graph.build(d)
        nodes = data["drawflow"]["Home"]["data"]
        self.assertEqual(len(nodes["2"]["outputs"]), 2)  # If: then + else
        self.assertEqual([c["node"] for c in nodes["2"]["outputs"]["output_1"]["connections"]], ["3", "4"])
        self.assertIn("LOGIC.IF", nodes["2"]["html"])
        self.assertIn("tb-off", nodes["5"]["class"])
        self.assertEqual((nodes["3"]["pos_x"], nodes["4"]["pos_y"]), (nodes["4"]["pos_x"], 130))  # stacked
        wires = list(d.wires)
        self.graph.read(data, d)
        self.assertEqual(sorted(d.wires, key=str), sorted(wires, key=str))
        self.assertEqual(d.nodes[0].box, (350.0, 20.0))

    def test_a_stop_dot_comes_after_the_run_dot_and_before_the_data_dots(self) -> None:
        def loop_ports(action: str, params: dict) -> tuple[str, ...]:
            return ("each", "stopped") if action == "logic.loop" else ("done",)

        graph = DrawflowGraph(loop_ports, str, data_inputs_of=lambda n: ["rounds"] if n.action == "logic.loop" else [],
                              data_outputs_of=lambda n: [("", "result")] if n.action == "a.count" else [],
                              entries_of=lambda n: ["stop"] if n.action == "logic.loop" else [])
        d = FlowDraft("f", "F", nodes=[NodeDraft("n1", "logic.loop", {"rounds": "${box.n2}"}),
                                       NodeDraft("n2", "a.count")],
                      wires=[FlowWire("start", "out", "n1"), FlowWire("start", "out", "n1", "stop")])
        data = graph.build(d)
        loop = data["drawflow"]["Home"]["data"]["2"]
        self.assertEqual(list(loop["inputs"]), ["input_1", "input_2", "input_3"])
        self.assertEqual([c["node"] for c in loop["inputs"]["input_1"]["connections"]], ["1"])
        self.assertEqual([c["node"] for c in loop["inputs"]["input_2"]["connections"]], ["1"])  # stop
        self.assertEqual([c["node"] for c in loop["inputs"]["input_3"]["connections"]], ["3"])  # rounds
        # its own run dot is named start, each extra one has its own colour (his round 55)
        self.assertIn('<span class="tb-run-dot tb-entry-start">start</span>', loop["html"])
        self.assertIn('class="tb-in tb-entry tb-entry-stop"', loop["html"])
        self.assertNotIn("tb-run-dot", data["drawflow"]["Home"]["data"]["3"]["html"])
        wires, params = list(d.wires), dict(d.nodes[0].params)
        d.nodes[0].params["rounds"] = "${box}"
        graph.read(data, d)
        self.assertEqual(sorted(d.wires, key=str), sorted(wires, key=str))
        self.assertEqual(d.nodes[0].params, params)

    def test_rewire_and_delete_in_the_browser(self) -> None:
        d = draft()
        data = self.graph.build(d)
        nodes = data["drawflow"]["Home"]["data"]
        del nodes["4"]  # n3 deleted
        nodes["3"]["outputs"]["output_1"]["connections"] = [{"node": "5", "output": "input_1"}]  # n2 → n4
        self.graph.read(data, d)
        self.assertEqual([n.id for n in d.nodes], ["n1", "n2", "n4"])
        self.assertIn(FlowWire("n2", "done", "n4"), d.wires)
        self.assertNotIn("n3", {w.target for w in d.wires})


if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
