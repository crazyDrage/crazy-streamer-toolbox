import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.boxes.add_to_list import AddToList
from streamer_toolbox.core.data.boxes.find_in_list import FindInList
from streamer_toolbox.core.data.boxes.get_from_list import GetFromList
from streamer_toolbox.core.data.boxes.insert_into_list import InsertIntoList
from streamer_toolbox.core.data.boxes.list_has import ListHas
from streamer_toolbox.core.data.boxes.list_size import ListSize
from streamer_toolbox.core.data.boxes.random_from_list import RandomFromList
from streamer_toolbox.core.data.boxes.remove_at_position import RemoveAtPosition
from streamer_toolbox.core.data.boxes.remove_from_list import RemoveFromList
from streamer_toolbox.core.data.boxes.shuffle_list import ShuffleList
from streamer_toolbox.core.data.boxes.sort_list import SortList
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
        await AddToList(self.variables).run("vts_saves", "desk")
        await AddToList(self.variables).run("vts_saves", "couch")
        await AddToList(self.variables).run("vts_saves", "bed", where="start")
        self.assertEqual(await AddToList(self.variables).run("vts_saves", "DESK", only_once="true"), ["bed", "desk", "couch"])
        await AddToList(self.variables).run("vts_saves", "desk")
        self.assertEqual(await RemoveFromList(self.variables).run("vts_saves", "Desk"), ["bed", "couch"])
        self.assertEqual(self.variables.get("vts_saves"), ["bed", "couch"])
        with self.assertRaises(ValueError):
            await AddToList(self.variables).run("vts_saves", "x", where="middle")
        self.variables.set("scene", "desktop")
        with self.assertRaises(ValueError):
            await AddToList(self.variables).run("scene", "x")

    async def test_reading(self) -> None:
        items = ["hat", "fan", "cape"]
        self.assertTrue(await ListHas().run(items, "FAN"))
        self.assertFalse(await ListHas().run('["hat"]', "fan"))
        self.assertEqual(await ListSize().run(""), 0)
        self.assertEqual(await GetFromList().run(items, 1), "hat")
        self.assertEqual(await GetFromList().run(items, "-1"), "cape")
        for position in (0, 4, -4):
            with self.assertRaises(IndexError):
                await GetFromList().run(items, position)
        self.assertIn(await RandomFromList().run(items), items)
        with self.assertRaises(IndexError):
            await RandomFromList().run([])

    async def test_registered_with_menu_groups(self) -> None:
        actions = ActionRegistry()
        self.lists.add_to(actions)
        self.assertEqual(actions.get("list.contains").ports, ("then", "else"))
        self.assertEqual(actions.get("list.add").group, "Change")
        self.assertEqual(await actions.get("list.add").options["where"](), ["end", "start"])

    async def test_new_list_boxes(self) -> None:
        names = ["right_arm", "left_arm", "right_leg"]
        self.assertEqual(await FindInList().run(names, "LEFT_ARM"), 2)
        self.assertEqual(await FindInList().run(names, "tail"), 0)
        self.assertEqual(await InsertIntoList().run(names, "left_leg"), [*names, "left_leg"])
        self.assertEqual(await InsertIntoList().run(names, "tail", 1), ["tail", *names])
        self.assertEqual(await RemoveAtPosition().run(names, -1), ["right_arm", "left_arm"])
        self.assertEqual(names, ["right_arm", "left_arm", "right_leg"])  # the original stays
        self.assertEqual(await SortList().run(["b", 10, "A", 2]), [2, 10, "A", "b"])
        top = [{"user": "kit", "value": 1}, {"user": "vex", "value": 3}]
        self.assertEqual(await SortList().run(top, "true", "value"), [top[1], top[0]])
        self.assertEqual(sorted(await ShuffleList().run(names)), sorted(names))
        self.assertEqual(await GetFromList().run(["ll"], 2, default=5), 5)

if __name__ == "__main__":
    unittest.main()
