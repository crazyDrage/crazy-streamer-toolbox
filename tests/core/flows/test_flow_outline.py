import unittest

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_outline import FlowOutline
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.outline_entry import OutlineEntry


def ports(action: str, params: dict) -> tuple[str, ...]:
    return ("then", "else") if action == "logic.if" else ("done",)


class TestFlowOutline(unittest.TestCase):
    def test_chain_parallel_if_and_merge(self) -> None:
        nodes = tuple(FlowNode(i, "logic.if" if i == "if" else "a.x") for i in ("get", "if", "t", "e", "s1", "s2", "x"))
        wires = (FlowWire("start", "out", "get"), FlowWire("get", "done", "if"),
                 FlowWire("if", "then", "t"), FlowWire("if", "else", "e"),
                 FlowWire("t", "done", "s1"), FlowWire("t", "done", "s2"), FlowWire("e", "done", "s1"))
        outline = FlowOutline(Flow("f", "F", nodes, wires), ports)
        entries = outline.build()
        node = lambda i: OutlineEntry("node", i)
        self.assertEqual(entries, (
            node("get"),
            OutlineEntry("node", "if", (
                ("then", (node("t"), OutlineEntry("parallel", branches=(("", (node("s1"),)), ("", (node("s2"),)))))),
                ("else", (node("e"), OutlineEntry("ref", "s1"))),
            )),
        ))
        self.assertEqual(outline.loose(), ["x"])


if __name__ == "__main__":
    unittest.main()
