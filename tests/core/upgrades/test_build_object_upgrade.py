import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.boxes.build_object import BuildObject
from streamer_toolbox.core.data.boxes.join_objects import JoinObjects
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.upgrades.build_object_upgrade import BuildObjectUpgrade
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestBuildObjectUpgrade(unittest.TestCase):
    """Settings version 8, his 11-22: Build object's five pairs become lines, its start object a Join objects box."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.actions = ActionRegistry()
        self.actions.add_box(BuildObject(), "object")
        self.actions.add_box(JoinObjects(), "object")
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"),
                                 FlowRunner(self.actions, VariableStore(folder / "variables")), self.actions)
        self.flows.load()
        self.upgrade = BuildObjectUpgrade(self.flows)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_pairs_become_lines(self) -> None:
        old = {"name_1": "id", "value_1": "${var.item.id}", "name_2": " ", "value_2": "left out",
               "name_3": "id", "value_3": 4, "name_4": "counter", "value_4": 0}
        self.flows.save(Flow("f", "F", (FlowNode("n1", "object.build", old, box=(10.0, 20.0)),)))
        said = self.upgrade.run()
        node = self.flows.get("f").nodes[0]
        self.assertEqual({"id": 4, "counter": 0}, node.params)  # the later "id" wins, as before
        self.assertEqual(["flow 'F': Build object as lines"], said)
        self.assertEqual([], self.upgrade.run())  # a second run changes nothing

    def test_a_start_object_becomes_a_join_objects_box_and_the_flow_gives_the_same(self) -> None:
        old = {"start": "${var.base}", "name_1": "b", "value_1": 2}
        reader = FlowNode("n2", "logic.end", {"all": "${box.n1}", "only_b": "${box.n1.b}"})
        self.flows.save(Flow("f", "F", (FlowNode("n1", "object.build", old, box=(10.0, 20.0)), reader)))
        said = self.upgrade.run()
        nodes = {node.id: node for node in self.flows.get("f").nodes}
        self.assertEqual({"b": 2}, nodes["n1"].params)
        join = nodes["n3"]
        self.assertEqual(("object.join", {"first": "${var.base}", "second": "${box.n1}"}, (310.0, 20.0)),
                         (join.action, join.params, join.box))
        self.assertEqual({"all": "${box.n3}", "only_b": "${box.n3.b}"}, nodes["n2"].params)
        self.assertIn("1 start object(s) now a Join objects box", said[0])
        # what the old box gave: the start object with the pairs on top
        self.assertEqual({"a": 1, "b": 2}, asyncio.run(JoinObjects().run({"a": 1}, asyncio.run(
            BuildObject().run(**nodes["n1"].params)))))

    def test_an_empty_start_and_other_boxes_stay(self) -> None:
        self.flows.save(Flow("f", "F", (FlowNode("n1", "object.build", {"start": "", "name_1": "a", "value_1": 1}),
                                        FlowNode("n2", "text.build", {"text": "{a}", "a": "${box.n1.a}"}))))
        self.upgrade.run()
        nodes = self.flows.get("f").nodes
        self.assertEqual(2, len(nodes))
        self.assertEqual({"a": 1}, nodes[0].params)
        self.assertEqual({"text": "{a}", "a": "${box.n1.a}"}, nodes[1].params)
        new = Flow("g", "G", (FlowNode("n1", "object.build", {"a": 1}),))
        self.assertIs(new, self.upgrade.flow(new))  # already lines: nothing to do


if __name__ == "__main__":
    unittest.main()
