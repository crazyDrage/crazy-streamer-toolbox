import unittest

from streamer_toolbox.core.flows.box_wire import is_wire_in
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import DrawflowGraph
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


def ports(action: str, params: dict) -> tuple[str, ...]:
    return ("then", "else") if action == "logic.if" else ("done",)


def data_inputs(node: NodeDraft) -> list[str]:
    return [k for k, v in node.params.items() if is_wire_in(v)]


def data_outputs(node: NodeDraft) -> list[tuple[str, str]]:
    if node.action == "data.split":
        return [(f, f"{f} · {k}") for f, k in node.params.get("fields", {}).items()]
    return [] if node.action == "logic.if" else [("", "result")]


def draft() -> FlowDraft:
    # Get position → Split (x, y) → If left; the If also reads n1.model straight from n1's result dot
    return FlowDraft("f", "F", nodes=[
        NodeDraft("n1", "vts.get_model_position"),
        NodeDraft("n2", "data.split", {"data": "${box.n1}", "fields": {"x": "number", "y": "number"}}),
        NodeDraft("n3", "logic.if", {"left": "${box.n2.y}", "op": "==", "right": "${box.n1.model}"})],
        wires=[FlowWire("start", "out", "n3")])


class TestDrawflowGraphDataWires(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = DrawflowGraph(ports, lambda a: a, data_inputs, data_outputs)

    def test_data_dots_come_after_the_run_dots_and_round_trip(self) -> None:
        d = draft()
        data = self.graph.build(d)
        nodes = data["drawflow"]["Home"]["data"]
        split, check = nodes["3"], nodes["4"]
        self.assertEqual((len(split["inputs"]), len(split["outputs"])), (2, 3))  # run + data | done + x + y
        self.assertEqual(check["inputs"]["input_2"]["connections"], [{"node": "3", "input": "output_3"}])  # y
        self.assertEqual(check["inputs"]["input_3"]["connections"], [{"node": "2", "input": "output_2"}])  # result
        self.assertNotIn("${box", check["html"])  # wired fields are dots, not text
        before = {n.id: dict(n.params) for n in d.nodes}
        self.graph.read(data, d)
        self.assertEqual({n.id: n.params for n in d.nodes}, before)  # n1.model kept its field
        self.assertEqual(d.wires, [FlowWire("start", "out", "n3")])  # data wires aren't run wires

    def test_a_box_is_a_row_per_dot_with_the_names_inside(self) -> None:
        graph = DrawflowGraph(ports, lambda a: a, lambda node: ["left", "right"] if node.action == "logic.if" else
                              data_inputs(node), data_outputs,
                              value_of=lambda node, name: "" if is_wire_in(node.params[name]) else node.params[name],
                              start_outputs=lambda: [("user", "user"), ("video", "video (input)")])
        d = draft()
        d.node("n3").params["left"] = "5 <b>"
        boxes = graph.build(d)["drawflow"]["Home"]["data"]
        check = boxes["4"]["html"]
        self.assertEqual(check.count('class="tb-row'), 3)  # the title's row, then left / else and right
        self.assertIn('<span class="tb-out tb-port-then" title="then">then</span></div>', check)  # in the title's row
        self.assertIn('left<span class="tb-value"> = 5 &lt;b&gt;</span></span>'
                      '<span class="tb-out tb-port-else" title="else">else</span>', check)
        self.assertIn('<span class="tb-in " title="right">right</span></div>', check)  # wired: no value
        split = boxes["3"]["html"]
        self.assertEqual(split.count('class="tb-row'), 3)  # title, data | x, y
        self.assertIn('title="y · number">y · number</span>', split)
        start = boxes["1"]["html"]
        self.assertIn('<div class="tb-row tb-apart"><span class="tb-in " title=""></span>'
                      '<span class="tb-out tb-flow-input" title="video (input)">', start)

    def test_rewire_and_unwire_in_the_browser(self) -> None:
        d = draft()
        data = self.graph.build(d)
        nodes = data["drawflow"]["Home"]["data"]
        nodes["4"]["inputs"]["input_2"]["connections"] = [{"node": "3", "input": "output_2"}]  # left ← x
        nodes["4"]["inputs"]["input_3"]["connections"] = []  # right unwired: the field is free again
        self.graph.read(data, d)
        self.assertEqual((d.node("n3").params["left"], d.node("n3").params["right"]), ("${box.n2.x}", ""))

    def test_a_wire_drawn_onto_a_field_that_had_a_value_takes_its_place(self) -> None:
        graph = DrawflowGraph(ports, lambda a: a, lambda node: ["left", "right"] if node.action == "logic.if" else
                              data_inputs(node), data_outputs)
        d = draft()
        d.node("n3").params.update(left="5", right="")
        data = graph.build(d)
        check = data["drawflow"]["Home"]["data"]["4"]
        self.assertEqual(check["data"].get("wired", {}), {})
        graph.read(data, d)  # nothing drawn, nothing changed: the value stays
        self.assertEqual(d.node("n3").params["left"], "5")
        check["inputs"]["input_2"]["connections"] = [{"node": "3", "input": "output_3"}]  # left ← y
        graph.read(data, d)
        self.assertEqual((d.node("n3").params["left"], d.node("n3").params["right"]), ("${box.n2.y}", ""))

    def test_a_field_switched_to_a_value_after_drawing_is_left_alone(self) -> None:
        d = draft()
        data = self.graph.build(d)
        d.node("n3").params["left"] = "5"
        self.graph.read(data, d)
        self.assertEqual(d.node("n3").params["left"], "5")

    def test_a_deleted_box_leaves_its_fields_waiting_for_a_wire(self) -> None:
        d = draft()
        d.nodes = [n for n in d.nodes if n.id != "n2"]
        flow = d.to_flow()
        self.assertEqual(flow.node("n3").params["left"], "${box}")

    def test_start_has_a_dot_per_trigger_field_and_wires_from_it_round_trip(self) -> None:
        d = draft()
        d.node("n3").params["right"] = "${box.start.user}"
        graph = DrawflowGraph(ports, lambda a: a, data_inputs, data_outputs,
                              start_outputs=lambda: [("user", "user"), ("message", "message")])
        data = graph.build(d)
        start = data["drawflow"]["Home"]["data"]["1"]
        self.assertEqual(len(start["outputs"]), 3)  # out + user + message
        self.assertEqual(start["outputs"]["output_2"]["connections"], [{"node": "4", "output": "input_3"}])
        start["outputs"]["output_2"]["connections"] = []
        data["drawflow"]["Home"]["data"]["4"]["inputs"]["input_3"]["connections"] = [
            {"node": "1", "input": "output_3"}]  # rewired to message
        graph.read(data, d)
        self.assertEqual(d.node("n3").params["right"], "${box.start.message}")
        self.assertEqual(d.wires, [FlowWire("start", "out", "n3")])
