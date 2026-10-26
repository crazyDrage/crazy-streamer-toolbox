import unittest
from typing import Any

from fastapi import APIRouter

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.interfaces.field_editor import FieldEditor
from streamer_toolbox.core.interfaces.listener import Listener
from streamer_toolbox.core.interfaces.page import Page
from streamer_toolbox.core.interfaces.panel import Panel
from streamer_toolbox.core.interfaces.tool import Tool
from streamer_toolbox.core.interfaces.trigger import Trigger
from tests.fakes.fake_plugin_context import FakePluginContext


class TestPluginAdd(unittest.IsolatedAsyncioTestCase):
    """His round 57: every kind of thing a plugin adds has one class, and ctx.add takes any of them."""

    def setUp(self) -> None:
        self.actions = ActionRegistry()
        self.ctx = FakePluginContext("p", self.actions)

        class Double(Box):
            name = "double"
            label = "Double"
            help = "Twice the number"
            group = "Maths"
            outputs = {"twice": "number"}

            def __init__(self) -> None:
                self.options = {"n": self.choices}

            async def choices(self) -> list[str]:
                return ["1", "2"]

            async def run(self, n: float = 1) -> dict[str, float]:
                return {"twice": n * 2}

        self.double = Double

    async def test_a_box_class_becomes_a_box_with_every_option_it_set(self) -> None:
        self.assertEqual(self.ctx.add(self.double()), "p.double")
        box = self.actions.get("p.double")
        self.assertEqual((box.label, box.description, box.group, box.outputs),
                         ("Double", "Twice the number", "Maths", {"twice": "number"}))
        self.assertEqual(await box.options["n"](), ["1", "2"])
        self.assertEqual(await self.actions.run("p.double", n=4), {"twice": 8})

    def test_a_connection_s_boxes_get_its_id_in_front(self) -> None:
        self.assertEqual(self.actions.add_box(self.double(), "lamp"), "lamp.double")
        self.assertIn("lamp.double", self.actions)

    def test_a_trigger_fires_through_the_plugin(self) -> None:
        class Rang(Trigger):
            event = "rang"
            title = "Bell rang"
            fields = ("times",)

        rang = Rang()
        with self.assertRaisesRegex(RuntimeError, "isn't added yet"):
            rang.fire({"times": 1})
        self.assertEqual(self.ctx.add(rang), "p.rang")
        rang.fire({"times": 2})
        self.assertEqual(self.ctx.triggers, {"p.rang": ("Bell rang", ("times",))})
        self.assertEqual(self.ctx.published, [("p.rang", {"times": 2})])

    def test_the_screens_the_listener_the_routes_and_a_field_editor(self) -> None:
        class Card(Panel):
            title = "Card"
            section = "settings"

            def build(self) -> None:
                pass

        class Board(Tool):
            title = "Board"

            def build(self) -> None:
                pass

        class Own(Page):
            title = "Own"

            def build(self) -> None:
                pass

        class Ear(Listener):
            async def heard(self, kind: str, data: dict[str, Any]) -> None:
                pass

        class Steps(FieldEditor):
            kind = "steps"

            def build(self) -> None:
                pass

            @staticmethod
            def text(value: Any) -> str:
                return ""

        for thing in (Card(), Board(), Own(), Ear(), APIRouter()):
            self.ctx.add(thing)
        self.assertEqual(self.ctx.add(Steps), "p.steps")
        self.assertEqual((self.ctx.panels, [t for t, _ in self.ctx.tools], self.ctx.pages),
                         (["Card"], ["Board"], ["/plugins/p"]))
        self.assertEqual((len(self.ctx.listeners), len(self.ctx.routers)), (1, 1))
        self.assertEqual(self.ctx.field_editors, {"p.steps": Steps})

    def test_something_it_doesnt_know_or_a_box_without_a_name_is_refused(self) -> None:
        class Nameless(Box):
            async def run(self) -> None:
                pass

        with self.assertRaisesRegex(ValueError, "Nameless needs a name"):
            self.ctx.add(Nameless())
        with self.assertRaisesRegex(TypeError, "ctx.add takes a Box, .* not str"):
            self.ctx.add("box")


if __name__ == "__main__":
    unittest.main()
