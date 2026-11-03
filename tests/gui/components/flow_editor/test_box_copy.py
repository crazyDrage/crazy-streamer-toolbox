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
        clipboard.copy([source.node("n2")], "f")
        source.node("n2").params["right"] = "Dragon"  # changed after copying: the copy keeps what it was
        other = FlowDraft("g", "G")
        originals, wires, same_flow = clipboard.take("g")
        self.assertFalse(same_flow)
        pasted = other.add_copy(originals[0], same_flow)
        self.assertEqual(pasted.params, {"left": WIRE_IN, "op": "==", "right": "Human"})
        self.assertTrue(clipboard.take("f")[2])

    def test_several_boxes_keep_the_wires_among_them(self) -> None:
        d = draft()
        d.node("n1").box = (100.0, 40.0)
        d.node("n2").params["right"] = "is ${box.n1.name} here?"
        d.wires.append(FlowWire("n1", "out", "n2"))
        clipboard = BoxClipboard()
        clipboard.copy([d.node("n1"), d.node("n2")], "f", d.wires)
        originals, wires, same_flow = clipboard.take("g")
        self.assertEqual(wires, [FlowWire("n1", "out", "n2")])  # the wire from Start isn't among them
        other = FlowDraft("g", "G", nodes=[NodeDraft("n1", "vts.get_model")])
        made = other.add_copies(originals, wires, same_flow, spot=(500.0, 500.0))
        self.assertEqual([n.id for n in made], ["n2", "n3"])
        self.assertEqual(made[1].params["left"], "${box.n2}")  # follows its copy, also into another flow
        self.assertEqual(made[1].params["right"], "is ${box.n2.name} here?")
        self.assertEqual([n.box for n in made], [(500.0, 500.0), (700.0, 560.0)])
        self.assertEqual(other.wires, [FlowWire("n2", "out", "n3")])

    def test_a_wire_to_a_box_not_copied_stays_in_the_same_flow(self) -> None:
        d = draft()
        made = d.add_copies([d.node("n2")], [], same_flow=True)
        self.assertEqual(made[0].params["left"], "${box.n1}")
