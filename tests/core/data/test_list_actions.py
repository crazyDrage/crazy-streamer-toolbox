import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.list_actions import ListActions
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestListActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self.tmp.name) / "v.json")
        self.lists = ListActions(self.variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_add_and_remove_change_the_variable(self) -> None:
        await self.lists.add("vts_saves", "desk")
        await self.lists.add("vts_saves", "couch")
        await self.lists.add("vts_saves", "bed", where="start")
        self.assertEqual(await self.lists.add("vts_saves", "DESK", only_once="true"), ["bed", "desk", "couch"])
        await self.lists.add("vts_saves", "desk")
        self.assertEqual(await self.lists.remove("vts_saves", "Desk"), ["bed", "couch"])
        self.assertEqual(self.variables.get("vts_saves"), ["bed", "couch"])
        with self.assertRaises(ValueError):
            await self.lists.add("vts_saves", "x", where="middle")
        self.variables.set("scene", "desktop")
        with self.assertRaises(ValueError):
            await self.lists.add("scene", "x")

    async def test_reading(self) -> None:
        items = ["hat", "fan", "cape"]
        self.assertTrue(await ListActions.contains(items, "FAN"))
        self.assertFalse(await ListActions.contains('["hat"]', "fan"))
        self.assertEqual(await ListActions.size(""), 0)
        self.assertEqual(await ListActions.get(items, 1), "hat")
        self.assertEqual(await ListActions.get(items, "-1"), "cape")
        for position in (0, 4, -4):
            with self.assertRaises(IndexError):
                await ListActions.get(items, position)
        self.assertIn(await ListActions.pick_random(items), items)
        with self.assertRaises(IndexError):
            await ListActions.pick_random([])

    async def test_registered_with_menu_groups(self) -> None:
        actions = ActionRegistry()
        self.lists.add_to(actions)
        self.assertEqual(actions.get("list.contains").ports, ("then", "else"))
        self.assertEqual(actions.get("list.add").group, "Change")
        self.assertEqual(await actions.get("list.add").options["where"](), ["end", "start"])

    async def test_new_list_boxes(self) -> None:
        L = ListActions
        names = ["right_arm", "left_arm", "right_leg"]
        self.assertEqual(await L.find(names, "LEFT_ARM"), 2)
        self.assertEqual(await L.find(names, "tail"), 0)
        self.assertEqual(await L.insert(names, "left_leg"), [*names, "left_leg"])
        self.assertEqual(await L.insert(names, "tail", 1), ["tail", *names])
        self.assertEqual(await L.remove_at(names, -1), ["right_arm", "left_arm"])
        self.assertEqual(names, ["right_arm", "left_arm", "right_leg"])  # the original stays
        self.assertEqual(await L.sort(["b", 10, "A", 2]), [2, 10, "A", "b"])
        top = [{"user": "kit", "value": 1}, {"user": "vex", "value": 3}]
        self.assertEqual(await L.sort(top, "true", "value"), [top[1], top[0]])
        self.assertEqual(sorted(await L.shuffle(names)), sorted(names))
        self.assertEqual(await L.get(["ll"], 2, default=5), 5)

if __name__ == "__main__":
    unittest.main()
