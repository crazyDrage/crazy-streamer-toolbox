import tempfile
import tomllib
import unittest
from pathlib import Path

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire

OLD_STEPS = """
label = "Just Chatting"
[[steps]]
action = "obs.switch_scene"
params = { scene = "Just_chatting" }
[[steps]]
action = "vts.trigger_hotkey"
params = { hotkey = "tail on" }
enabled = false
[[triggers]]
kind = "twitch.redeem"
reward = "Big Action: clean screen"
"""


class TestFlowStore(unittest.TestCase):
    def test_reads_old_step_lists_as_a_chain_and_skips_broken_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "just_chatting.toml").write_text(OLD_STEPS, encoding="utf-8")
            (folder / "broken.toml").write_text("steps = [ { nope", encoding="utf-8")
            flows = FlowStore(folder).all()
        self.assertEqual([f.name for f in flows], ["just_chatting"])
        flow = flows[0]
        self.assertEqual(flow.nodes[0], FlowNode("n1", "obs.switch_scene", {"scene": "Just_chatting"}))
        self.assertFalse(flow.nodes[1].enabled)
        self.assertEqual(flow.wires, (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        self.assertEqual(flow.triggers, (FlowTrigger("twitch.redeem", {"reward": "Big Action: clean screen"}),))

    def test_save_and_read_back(self) -> None:
        flow = Flow("sound", 'Sound "redeem"', (
            FlowNode("a", "vts.get_model_position", save_as="spot", box=(300, 80)),
            FlowNode("b", "logic.if", {"left": "${var.model}", "op": "contains", "right": "human"}),
            FlowNode("c", "vts.move_model_to", {"position": "${var.spot}", "seconds": 1.5}, False, "n"),
        ), (FlowWire("start", "out", "a"), FlowWire("start", "out", "b"), FlowWire("b", "then", "c")),
            (FlowTrigger("twitch.redeem", {"reward": "Big Action"}),), "plays it",
            (FlowInput("video"), FlowInput("volume", "80")), "queue", 30, 120.5, True)
        with tempfile.TemporaryDirectory() as tmp:
            store = FlowStore(Path(tmp) / "flows")
            store.save(flow)
            tomllib.loads(store.path_of("sound").read_text(encoding="utf-8"))  # valid TOML
            back = store.all()
            store.delete("sound")
            self.assertFalse(store.exists("sound"))
        self.assertEqual(back, [flow])

    def test_save_refuses_bad_file_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                FlowStore(Path(tmp)).save(Flow("../evil", "x"))

    def test_trigger_match_ignores_case(self) -> None:
        trigger = FlowTrigger("twitch.redeem", {"reward": "Big Action: clean screen"})
        self.assertTrue(trigger.matches("twitch.redeem", {"reward": "big action: CLEAN screen", "user": "x"}))
        self.assertFalse(trigger.matches("twitch.redeem", {"reward": "other"}))
        self.assertFalse(trigger.matches("twitch.follow", {"reward": "Big Action: clean screen"}))
        chat = FlowTrigger("twitch.chat", {"message": "!qa *"})
        self.assertTrue(chat.matches("twitch.chat", {"message": "!QA how (are) you?"}))
        self.assertFalse(chat.matches("twitch.chat", {"message": "!qa"}))
        self.assertTrue(FlowTrigger("twitch.chat", {"message": "*"}).matches("twitch.chat", {"message": "hi"}))

    def test_data_wires_and_split_fields_survive_a_save(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "data.split", {"data": "${box.n2}",
                                                             "fields": {"x": "number", "model": "text"}}),
                               FlowNode("n2", "logic.if", {"left": "${box}", "right": "${box.n1.x}"})))
        with tempfile.TemporaryDirectory() as tmp:
            store = FlowStore(Path(tmp))
            store.save(flow)
            self.assertEqual(store.all()[0].nodes, flow.nodes)

    def test_a_wire_into_a_stop_dot_survives_a_save(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "logic.loop"),),
                    (FlowWire("start", "out", "n1"), FlowWire("start", "out", "n1", "stop")))
        with tempfile.TemporaryDirectory() as tmp:
            store = FlowStore(Path(tmp))
            store.save(flow)
            self.assertIn('entry = "stop"', (Path(tmp) / "f.toml").read_text(encoding="utf-8"))
            self.assertEqual(store.all()[0].wires, flow.wires)

    def test_a_value_the_box_keeps_survives_a_save(self) -> None:
        animation = {"relative": True, "base": {"x": 0.1, "y": 0.2, "rotation": 0.0, "size": 5.0},
                     "steps": [{"x": 0.2, "y": 0.0, "rotation": 10.0, "size": 0.0, "seconds": 1.0, "wait": 0.5}]}
        flow = Flow("f", "F", (FlowNode("n1", "vts.play_animation", {"animation": animation, "repeat": 2}),))
        with tempfile.TemporaryDirectory() as tmp:
            store = FlowStore(Path(tmp))
            store.save(flow)
            self.assertEqual(store.all()[0].nodes, flow.nodes)


if __name__ == "__main__":
    unittest.main()
