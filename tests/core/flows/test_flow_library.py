import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowLibrary(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.calls: list[dict] = []
        self.actions = ActionRegistry()

        async def record(**params):
            self.calls.append(params)

        self.actions.add("a.record", record)
        self.store = FlowStore(folder / "flows")
        runner = FlowRunner(self.actions, VariableStore(folder / "variables.json"))
        self.library = FlowLibrary(self.store, FlowStore(folder / "flow_templates"), runner, self.actions)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_edit_replaces_the_running_action(self) -> None:
        self.library.save(Flow("f", "F", (FlowNode("n1", "a.record", {"n": 1}),), (FlowWire("start", "out", "n1"),)))
        self.library.save(Flow("f", "F", (FlowNode("n1", "a.record", {"n": 2}),), (FlowWire("start", "out", "n1"),)))
        await self.actions.run("flow.f")
        self.assertEqual(self.calls, [{"n": 2}])
        self.assertTrue(self.store.exists("f"))

    def test_rename_and_delete_drop_the_old_action(self) -> None:
        self.library.save(Flow("old", "Old"))
        self.library.save(Flow("new", "New"), old_name="old")
        self.assertNotIn("flow.old", self.actions)
        self.assertFalse(self.store.exists("old"))
        self.library.delete("new")
        self.assertNotIn("flow.new", self.actions)
        self.assertEqual(self.library.all(), [])

    def test_load_and_free_names(self) -> None:
        self.store.save(Flow("just_chatting", "Just Chatting"))
        self.library.load()
        self.assertIn("flow.just_chatting", self.actions)
        self.assertEqual(self.library.free_name("Just Chatting!"), "just_chatting_2")
        self.assertEqual(self.library.free_name("???"), "flow")

    def test_templates_are_kept_apart(self) -> None:
        self.library.save_template(Flow("sound", "Sound"))
        self.assertEqual([t.name for t in self.library.templates()], ["sound"])
        self.assertEqual(self.library.free_template_name("Sound"), "sound_2")
        self.assertNotIn("flow.sound", self.actions)
        self.library.delete_template("sound")
        self.assertEqual(self.library.templates(), [])

    async def test_export_and_import(self) -> None:
        trigger = FlowTrigger("timer", {"every": 5})
        self.library.save(Flow("tick", "Tick", (FlowNode("n1", "a.record", {"n": 1}),),
                               (FlowWire("start", "out", "n1"),), (trigger,)))
        text = self.library.export_text("tick")
        self.assertIn('label = "Tick"', text)
        copy = self.library.import_text(text, "tick.toml")  # Tick exists: a copy without triggers
        self.assertEqual((copy.name, copy.label, copy.triggers), ("tick_imported", "Tick (imported)", ()))
        self.library.delete("tick")
        again = self.library.import_text(text, "tick.toml")  # nothing in the way: as it was, triggers too
        self.assertEqual((again.name, again.label, again.triggers), ("tick", "Tick", (trigger,)))
        await self.actions.run("flow.tick")
        self.assertEqual(self.calls, [{"n": 1}])
        for bad in ("not = [toml", 'label = "no boxes"'):
            with self.assertRaisesRegex(ValueError, "not a flow file"):
                self.library.import_text(bad, "x.toml")

    async def test_renaming_a_variable_changes_the_flows_and_templates_that_use_it(self) -> None:
        uses = Flow("f", "F", (FlowNode("n1", "a.record", {"x": "${var.spot.x}"}),), (FlowWire("start", "out", "n1"),))
        other = Flow("g", "G", (FlowNode("n1", "a.record", {"x": 1}),), (FlowWire("start", "out", "n1"),))
        self.library.save(uses)
        self.library.save(other)
        self.library.save_template(Flow("t", "T", (FlowNode("n1", "var.set", {"name": "spot", "value": 0}),)))
        self.assertEqual(self.library.rename_variable("spot", "dragon_spot"), ["F", "T (template)"])
        self.assertEqual(self.store.all()[0].node("n1").params, {"x": "${var.dragon_spot.x}"})
        self.assertEqual(self.library.templates()[0].node("n1").params["name"], "dragon_spot")
        self.assertEqual(self.library.get("f").node("n1").params["x"], "${var.dragon_spot.x}")  # the action too


    def test_folders_sort_flows_without_touching_their_files_or_actions(self) -> None:
        for name in ("lizard_add_1", "lizard_timer", "desktop"):
            self.library.save(Flow(name, name))
        self.library.move("lizard_add_1", " Lizard ")
        self.library.move("lizard_timer", "Lizard")
        self.assertEqual(self.library.folders(), ["Lizard"])
        self.assertEqual(self.store.all()[1].folder, "Lizard")  # in the file (A-Z: desktop, lizard_add_1, ...)
        self.assertIn("flow.lizard_add_1", self.actions)
        self.library.rename_folder("Lizard", "Lizard stuff")
        self.assertEqual({f.name: f.folder for f in self.library.all()},
                         {"desktop": "", "lizard_add_1": "Lizard stuff", "lizard_timer": "Lizard stuff"})
        self.library.rename_folder("Lizard stuff", "")
        self.assertEqual(self.library.folders(), [])

    async def test_a_folder_goes_out_and_comes_in_as_one_file(self) -> None:
        self.library.save(Flow("add", "Add", (FlowNode("n1", "a.record", {"n": 1}),),
                               (FlowWire("start", "out", "n1"),), folder="lizard"))
        self.library.save(Flow("plus_one", "Plus one", (FlowNode("n1", "flow.add"),), (FlowWire("start", "out", "n1"),),
                               (FlowTrigger("timer", {"every": 5}),), folder="lizard"))
        self.library.save(Flow("other", "Other"))
        text = self.library.folder_pack("lizard").to_text()

        copies = self.library.import_file(text, "lizard.flows.toml")  # both labels are taken here
        self.assertEqual([(f.name, f.label, f.folder, f.triggers) for f in copies],
                         [("add_imported", "Add (imported)", "lizard", ()),
                          ("plus_one_imported", "Plus one (imported)", "lizard", ())])
        self.assertEqual(copies[1].nodes[0].action, "flow.add_imported")  # its box runs the copy, not the old one
        await self.actions.run("flow.plus_one_imported")
        self.assertEqual(self.calls, [{"n": 1}])

        for flow in self.library.all():
            self.library.delete(flow.name)
        fresh = self.library.import_file(text, "lizard.flows.toml")  # an empty toolbox: as they were
        self.assertEqual([(f.name, f.label, len(f.triggers)) for f in fresh],
                         [("add", "Add", 0), ("plus_one", "Plus one", 1)])

    def test_import_file_takes_one_flow_too_and_says_what_is_wrong(self) -> None:
        self.library.save(Flow("tick", "Tick", (FlowNode("n1", "a.record"),), (FlowWire("start", "out", "n1"),)))
        self.assertEqual([f.label for f in self.library.import_file(self.library.export_text("tick"), "tick.toml")],
                         ["Tick (imported)"])
        for bad in ("toolbox_flows = 1", "toolbox_flows = 2\n[[flows]]\nname = 'a'", "not toml ["):
            with self.assertRaises(ValueError):
                self.library.import_file(bad, "x.toml")

    def test_a_folder_file_brings_the_flows_its_boxes_use(self) -> None:
        wires = (FlowWire("start", "out", "n1"),)
        self.library.save(Flow("deep", "Deep"))
        self.library.save(Flow("helper", "Helper", (FlowNode("n1", "flow.deep"),), wires, folder="tools"))
        self.library.save(Flow("plus", "Plus", (FlowNode("n1", "flow.helper"), FlowNode("n2", "flow.gone")), wires,
                               folder="lizard"))
        pack = self.library.folder_pack("lizard")
        self.assertEqual([f.name for f in pack.flows], ["plus", "helper", "deep"])
        self.assertEqual(pack.needs(), ["gone"])  # deleted here: nothing to bring


if __name__ == "__main__":
    unittest.main()
