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

    def test_rewire_and_unwire_in_the_browser(self) -> None:
        d = draft()
        data = self.graph.build(d)
        nodes = data["drawflow"]["Home"]["data"]
        nodes["4"]["inputs"]["input_2"]["connections"] = [{"node": "3", "input": "output_2"}]  # left ← x
        nodes["4"]["inputs"]["input_3"]["connections"] = []  # right unwired
        self.graph.read(data, d)
        self.assertEqual((d.node("n3").params["left"], d.node("n3").params["right"]), ("${box.n2.x}", "${box}"))

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
