import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestLogicActions(unittest.IsolatedAsyncioTestCase):
    async def test_compare(self) -> None:
        compare = LogicActions.compare
        self.assertTrue(await compare("Desktop", "==", "desktop"))
        self.assertTrue(await compare("CrazyDrage Human (Ready to Rig)", "contains", "HUMAN"))
        self.assertTrue(await compare("10", ">", 9.5))
        self.assertTrue(await compare(3, "!=", "4"))
        self.assertFalse(await compare("a", "==", "b"))
        with self.assertRaises(ValueError):
            await compare("a", "<", "b")

    async def test_set_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            await LogicActions(store).set_variable("scene", "desktop")
            self.assertEqual(store.get("scene"), "desktop")
            logic = LogicActions(store)
            self.assertEqual(await logic.add_to_variable("lizard_timer", 10), 10)
            self.assertEqual(await logic.add_to_variable("lizard_timer", "-1"), 9)
            self.assertEqual(await logic.add_to_variable("spin", 0.5), 0.5)
            with self.assertRaises(ValueError):
                await logic.add_to_variable("scene", 1)

    async def test_set_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            logic = LogicActions(store)
            await logic.set_field("save", "modelName", "Dragon")
            before = await logic.set_field("save", "position.x", 0.5)
            self.assertEqual(await logic.set_field("save", "position.y", -1),
                             {"modelName": "Dragon", "position": {"x": 0.5, "y": -1}})
            self.assertEqual(before, {"modelName": "Dragon", "position": {"x": 0.5}})  # a copy, not changed later
            with self.assertRaises(ValueError):
                await logic.set_field("save", "modelName.x", 1)
            store.set("scene", "desktop")
            with self.assertRaises(ValueError):
                await logic.set_field("scene", "x", 1)
            store.set("typed", '{"a": 1}')  # Set variable keeps what was typed as text
            self.assertEqual(await logic.set_field("typed", "b.c", 5), {"a": 1, "b": {"c": 5}})

    async def test_for_each_sets_the_item_before_each_round(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            seen = []
            async for port in await LogicActions(store).for_each('["hat", "fan"]', "thing"):
                seen.append((port, store.get("thing")))
            self.assertEqual(seen, [("each", "hat"), ("each", "fan"), ("done", "fan")])
            with self.assertRaises(ValueError):
                await LogicActions(store).for_each("hat", "thing")

    async def test_calculate(self) -> None:
        self.assertEqual(await LogicActions.calculate(0.5, "-", 0.2), 0.3)
        self.assertEqual(await LogicActions.calculate("3", "*", "4"), 12)
        self.assertEqual(await LogicActions.calculate(1, "/", 4), 0.25)
        with self.assertRaises(ValueError):
            await LogicActions.calculate("left", "+", 1)
        with self.assertRaises(ValueError):
            await LogicActions.calculate(1, "/", 0)

    async def test_round_clamp_switch(self) -> None:
        self.assertEqual(await LogicActions.round_number("2.6"), 3)
        self.assertEqual(await LogicActions.round_number(2.345, 2), 2.35)
        self.assertEqual(await LogicActions.clamp("15", 1, 10), 10)
        self.assertEqual(await LogicActions.clamp(-3, 1, 10), 1)
        self.assertEqual(await LogicActions.clamp(4.5, 1, 10), 4.5)
        cases = {"case_1": "ra, right_arm", "case_2": "la, left_arm", "case_4": "5"}
        self.assertEqual(await LogicActions.switch("RA", **cases), "case_1")
        self.assertEqual(await LogicActions.switch("left_arm", **cases), "case_2")
        self.assertEqual(await LogicActions.switch(5, **cases), "case_4")
        self.assertEqual(await LogicActions.switch("tail", **cases), "else")
        self.assertEqual(await LogicActions.switch("", **cases), "else")  # empty cases never match

    async def test_repeat_and_random(self) -> None:
        self.assertEqual(await LogicActions.repeat(3), ["each", "each", "each", "done"])
        self.assertEqual(await LogicActions.repeat(0), ["done"])
        rolls = {await LogicActions.random_number(1, 6) for _ in range(200)}
        self.assertEqual(rolls, {1, 2, 3, 4, 5, 6})


if __name__ == "__main__":
    unittest.main()
