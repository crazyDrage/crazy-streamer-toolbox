import unittest

from streamer_toolbox.core.flows.box_wire import WIRE_IN
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.gui.components.flow_editor.box_clipboard import BoxClipboard
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft


def draft(name: str = "f") -> FlowDraft:
    return FlowDraft(name, "F", nodes=[
        NodeDraft("n1", "vts.get_model"),
        NodeDraft("n2", "logic.if", {"left": "${box.n1}", "op": "==", "right": "Human"}, note="check",
                  box=(300.0, 100.0))],
        wires=[FlowWire("start", "out", "n2")])


class TestBoxCopy(unittest.TestCase):
    def test_duplicate_is_a_new_unwired_box_with_the_same_settings(self) -> None:
        d = draft()
        copy = d.add_copy(d.node("n2"), same_flow=True)
        self.assertEqual(copy.id, "n3")
        self.assertEqual(copy.params, {"left": "${box.n1}", "op": "==", "right": "Human"})  # same orange wire
        self.assertEqual((copy.note, copy.box), ("check", (340.0, 160.0)))
        self.assertEqual([w for w in d.wires if w.target == "n3"], [])  # no run wire

    def test_paste_into_another_flow_drops_the_orange_wires(self) -> None:
        clipboard = BoxClipboard()
        self.assertIsNone(clipboard.take("f"))
        source = draft("f")
        clipboard.copy(source.node("n2"), "f")
        source.node("n2").params["right"] = "Dragon"  # changed after copying: the copy keeps what it was
        other = FlowDraft("g", "G")
        original, same_flow = clipboard.take("g")
        self.assertFalse(same_flow)
        pasted = other.add_copy(original, same_flow)
        self.assertEqual(pasted.params, {"left": WIRE_IN, "op": "==", "right": "Human"})
        self.assertTrue(clipboard.take("f")[1])
