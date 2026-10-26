import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.flows.boxes.calculate import Calculate
from streamer_toolbox.core.flows.boxes.clamp import Clamp
from streamer_toolbox.core.flows.boxes.color_from_numbers import ColorFromNumbers
from streamer_toolbox.core.flows.boxes.for_each import ForEach
from streamer_toolbox.core.flows.boxes.if_box import IfBox
from streamer_toolbox.core.flows.boxes.random_number import RandomNumber
from streamer_toolbox.core.flows.boxes.repeat import Repeat
from streamer_toolbox.core.flows.boxes.round_number import RoundNumber
from streamer_toolbox.core.flows.boxes.switch import Switch
from streamer_toolbox.core.flows.boxes.value import Value
from streamer_toolbox.core.variables.boxes.get_variable import GetVariable
from streamer_toolbox.core.variables.boxes.math_on_variable import MathOnVariable
from streamer_toolbox.core.variables.boxes.set_field import SetField
from streamer_toolbox.core.variables.boxes.set_variable import SetVariable
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestLogicBoxes(unittest.IsolatedAsyncioTestCase):
    async def test_compare(self) -> None:
        compare = IfBox().run
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
            await SetVariable(store).run("scene", "desktop")
            self.assertEqual(store.get("scene"), "desktop")
            math = MathOnVariable(store).run
            self.assertEqual(await math("lizard_timer", "+", 10), 10)
            self.assertEqual(await math("lizard_timer", amount="-1"), 9)  # an old Add box
            self.assertEqual(await math("lizard_timer", "*", 2), 18)
            self.assertEqual(await math("lizard_timer", "/", 4), 4.5)
            self.assertEqual(await math("lizard_timer", "-", 0.5), 4)
            self.assertEqual(await math("spin", "+", 0.5), 0.5)
            self.assertEqual(store.get("lizard_timer"), 4)
            with self.assertRaises(ValueError):
                await math("scene", "+", 1)
            with self.assertRaises(ValueError):
                await math("lizard_timer", "/", 0)
            self.assertEqual(store.get("lizard_timer"), 4)  # a failed one changes nothing

    async def test_get_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            store.set("pos", {"x": 0.5, "inner": {"y": 2}})
            get = GetVariable(store).run
            self.assertEqual(await get("pos"), {"x": 0.5, "inner": {"y": 2}})
            self.assertEqual(await get("pos", "x"), 0.5)
            self.assertEqual(await get("pos", "inner.y"), 2)
            with self.assertRaises(KeyError):
                await get("nothing")
            with self.assertRaises(KeyError):
                await get("pos", "z")

    async def test_value_gives_its_lines_by_name(self) -> None:
        self.assertEqual(await Value().run({"power": 10, "model": "Hex"}), {"power": 10, "model": "Hex"})
        self.assertEqual(await Value().run(value=7), 7)  # a box from before the lines, sent by the API

    async def test_set_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            set_field = SetField(store).run
            await set_field("save", "modelName", "Dragon")
            before = await set_field("save", "position.x", 0.5)
            self.assertEqual(await set_field("save", "position.y", -1),
                             {"modelName": "Dragon", "position": {"x": 0.5, "y": -1}})
            self.assertEqual(before, {"modelName": "Dragon", "position": {"x": 0.5}})  # a copy, not changed later
            with self.assertRaises(ValueError):
                await set_field("save", "modelName.x", 1)
            store.set("scene", "desktop")
            with self.assertRaises(ValueError):
                await set_field("scene", "x", 1)
            store.set("typed", '{"a": 1}')  # Set variable keeps what was typed as text
            self.assertEqual(await set_field("typed", "b.c", 5), {"a": 1, "b": {"c": 5}})

    async def test_for_each_sets_the_item_before_each_round(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            seen = []
            async for port in await ForEach(store).run('["hat", "fan"]', "thing"):
                seen.append((port, store.get("thing")))
            self.assertEqual(seen, [("each", "hat"), ("each", "fan"), ("done", "fan")])
            with self.assertRaises(ValueError):
                await ForEach(store).run("hat", "thing")

    async def test_calculate(self) -> None:
        self.assertEqual(await Calculate().run(0.5, "-", 0.2), 0.3)
        self.assertEqual(await Calculate().run("3", "*", "4"), 12)
        self.assertEqual(await Calculate().run(1, "/", 4), 0.25)
        with self.assertRaises(ValueError):
            await Calculate().run("left", "+", 1)
        with self.assertRaises(ValueError):
            await Calculate().run(1, "/", 0)

    async def test_round_clamp_switch(self) -> None:
        self.assertEqual(await RoundNumber().run("2.6"), 3)
        self.assertEqual(await RoundNumber().run(2.345, 2), 2.35)
        self.assertEqual(await Clamp().run("15", 1, 10), 10)
        self.assertEqual(await Clamp().run(-3, 1, 10), 1)
        self.assertEqual(await Clamp().run(4.5, 1, 10), 4.5)
        cases = {"case_1": "ra, right_arm", "case_2": "la, left_arm", "case_4": "5"}
        self.assertEqual(await Switch().run("RA", **cases), "case_1")
        self.assertEqual(await Switch().run("left_arm", **cases), "case_2")
        self.assertEqual(await Switch().run(5, **cases), "case_4")
        self.assertEqual(await Switch().run("tail", **cases), "else")
        self.assertEqual(await Switch().run("", **cases), "else")  # empty cases never match

    async def test_colour_from_numbers(self) -> None:
        self.assertEqual(await ColorFromNumbers().run(255, "128", 0), "#FF8000")
        self.assertEqual(await ColorFromNumbers().run(270, -15, 14.6), "#FF000F")  # kept inside 0-255, rounded
        with self.assertRaisesRegex(ValueError, "three numbers"):
            await ColorFromNumbers().run(255, "red", 0)

    async def test_repeat_and_random(self) -> None:
        self.assertEqual(await Repeat().run(3), ["each", "each", "each", "done"])
        self.assertEqual(await Repeat().run(0), ["done"])
        rolls = {await RandomNumber().run(1, 6) for _ in range(200)}
        self.assertEqual(rolls, {1, 2, 3, 4, 5, 6})


if __name__ == "__main__":
    unittest.main()
