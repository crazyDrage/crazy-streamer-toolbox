import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.plugins.plugin_loader import PluginLoader
from tests.fakes.fake_plugin_context import FakePluginContext

PLUGINS = Path(__file__).resolve().parents[2] / "plugins"


class TestExamplePlugin(unittest.IsolatedAsyncioTestCase):
    """The example plugin is what people copy: it has to load and do what its README says."""

    def setUp(self) -> None:
        self.actions = ActionRegistry()
        self.contexts: dict[str, FakePluginContext] = {}

        def make_context(plugin_id: str, folder) -> FakePluginContext:
            self.contexts[plugin_id] = FakePluginContext(plugin_id, self.actions, answer=True, folder=folder)
            return self.contexts[plugin_id]

        loader = PluginLoader(PLUGINS, make_context, lambda: [])
        loader.load_all({"example"})
        self.assertEqual((loader.loaded, loader.failed), (["example"], {}))
        self.ctx = self.contexts["example"]
        self.lamp = self.ctx.connections[0]
        self.lamp.add_actions(self.actions)  # the toolbox does this for every connection at start

    def test_it_adds_one_of_everything(self) -> None:
        ctx = self.ctx
        self.assertEqual((self.lamp.id, self.lamp.title), ("example", "Example lamp"))
        self.assertEqual(ctx.triggers, {"example.blinked": ("Example lamp blinked", ("times", "color"))})
        self.assertEqual(ctx.trigger_choices, {"example.blinked": ("*", "white", "red", "green", "blue", "purple")})
        self.assertEqual([title for title, _ in ctx.tools], ["Example lamp"])
        self.assertEqual((ctx.panels, ctx.pages, len(ctx.routers), len(ctx.listeners)),
                         (["Example lamp"], ["/plugins/example"], 1, 1))
        for name in ("shout", "ask_then_blink", "switch", "set_color", "blink", "get_color"):
            self.assertIn(f"example.{name}", self.actions)
        self.assertTrue(self.actions.get("example.get_color").live)
        self.assertEqual(self.actions.get("example.blink").group, "Effects")
        for file in ("README.md", "resources/settings.json", "resources/lamp.svg"):
            self.assertTrue((PLUGINS / "example" / file).is_file(), file)

    async def test_the_lamp_is_off_until_connected_and_its_boxes_say_so(self) -> None:
        self.assertFalse(self.lamp.settings["enabled"])
        with self.assertRaisesRegex(NotConnectedError, "switched off under Connections"):
            await self.actions.run("example.blink")
        self.assertEqual((await self.lamp.test({"name": " "})).detail, "The lamp needs a name")
        self.lamp.configure({"enabled": True})  # what Connect does, with the default name
        with self.assertRaisesRegex(NotConnectedError, "not connected"):
            await self.actions.run("example.blink")
        await self.lamp.start()
        self.assertEqual((self.lamp.status.state, self.lamp.status.facts[0]),
                         (ConnectionState.CONNECTED, ("Lamp", "Desk lamp")))
        await self.lamp.stop()
        self.assertEqual(self.lamp.status.state, ConnectionState.OFF)

    async def test_boxes_change_the_lamp_and_a_blink_is_told_to_the_toolbox(self) -> None:
        self.lamp.configure({"enabled": True})
        await self.lamp.start()
        self.assertEqual(await self.actions.get("example.set_color").options["color"](),
                         ["white", "red", "green", "blue", "purple"])
        self.assertEqual(await self.actions.run("example.set_color", color=" Red "),
                         {"color": "red", "before": "white"})
        with self.assertRaisesRegex(ValueError, "has no colour"):
            await self.actions.run("example.set_color", color="pink")
        self.assertEqual(await self.actions.run("example.blink", times=2, seconds=0), {"blinks": 1})
        self.assertEqual(self.ctx.published, [("example.blinked", {"times": 2, "color": "red"})])
        self.assertEqual(await self.actions.run("example.get_color"), {"color": "red", "on": True})
        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            await self.actions.run("example.blink", times=99)
        await self.actions.run("example.switch", on=False)
        self.assertEqual(await self.actions.run("example.get_color"), {"color": "red", "on": False})

    async def test_the_plain_box_the_question_and_the_listener(self) -> None:
        self.assertEqual(await self.actions.run("example.shout", text="hi", times=2), {"text": "HI! HI!"})
        self.lamp.configure({"enabled": True})
        await self.lamp.start()
        self.assertEqual(await self.actions.run("example.ask_then_blink"), {"blinked": True})
        self.assertEqual(self.ctx.questions, ["Blink the example lamp?"])
        self.ctx.answer = None  # nobody answered
        self.assertEqual(await self.actions.run("example.ask_then_blink"), {"blinked": False})
        self.assertEqual(len(self.ctx.published), 1)
        await self.ctx.tell("twitch.follow", {"user": "ann"})
        await self.ctx.tell("timer", {"every": 1})
        counter = self.ctx.listeners[0].__self__
        self.assertEqual((counter.count, counter.last), (1, "twitch.follow"))


if __name__ == "__main__":
    unittest.main()
