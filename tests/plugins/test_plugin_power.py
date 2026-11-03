import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.switched_off_error import SwitchedOffError
from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin
from streamer_toolbox.plugins.plugin_power import PluginPower
from streamer_toolbox.plugins.plugin_switches import PluginSwitches
from tests.fakes.fake_connection import FakeConnection


class TestPluginPower(unittest.IsolatedAsyncioTestCase):
    """His round 57: "off stops everything, even if it is used in a box"; on again, it all works again."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.calls: list[str] = []
        calls = self.calls

        class Recording(ToolboxPlugin):
            def __init__(self, plugin_id: str) -> None:
                self.plugin_id = plugin_id

            def register(self, ctx) -> None:
                pass

            async def start(self) -> None:
                calls.append(f"{self.plugin_id} start")

            async def stop(self) -> None:
                calls.append(f"{self.plugin_id} stop")
                if self.plugin_id == "broken":
                    raise RuntimeError("socket stuck")

        self.plugins = {pid: Recording(pid) for pid in ("broken", "lamp", "quiet")}
        self.switches = PluginSwitches(Path(self.tmp.name) / "plugins_off.json")
        self.power = PluginPower(self.switches, lambda: self.plugins)
        self.lamp = FakeConnection({"url": "good", "enabled": True})
        self.lamp.id = "lamp"
        self.connections = ConnectionManager([self.lamp], ConfigTableWriter(Path(self.tmp.name) / "toolbox.toml"),
                                             paused=self.power.is_off)
        self.power.connections = self.connections
        self.actions = ActionRegistry()
        self.actions.guard(self.power.why_not)

        async def blink() -> str:
            return "blinked"

        self.actions.add("lamp.blink", blink)
        self.actions.add("obs.blink", blink)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_off_stops_the_plugin_its_connection_and_its_boxes_and_on_brings_them_back(self) -> None:
        await self.power.switch("lamp", False)
        self.assertEqual((self.calls, self.lamp.calls), (["lamp stop"], ["stop"]))
        with self.assertRaisesRegex(SwitchedOffError, "The plugin lamp is switched off: switch it on under Plugins"):
            await self.actions.run("lamp.blink")
        self.assertEqual(await self.actions.run("obs.blink"), "blinked")  # others go on
        self.assertTrue(self.connections.is_paused("lamp"))
        await self.connections.check_all()  # not woken up by the keep-alive round either
        await self.power.switch("lamp", False)  # already off: nothing happens twice
        self.assertEqual(self.lamp.calls, ["stop"])
        await self.power.switch("lamp", True)
        self.assertEqual((self.calls, self.lamp.calls), (["lamp stop", "lamp start"], ["stop", "start"]))
        self.assertEqual(await self.actions.run("lamp.blink"), "blinked")

    async def test_the_toolbox_starts_and_stops_only_the_plugins_that_are_on_even_after_one_fails(self) -> None:
        self.switches.switch("quiet", False)
        await self.power.start_all()
        await self.connections.start_all()
        self.assertEqual(self.calls, ["broken start", "lamp start"])
        with self.assertLogs("streamer_toolbox.plugins.plugin_power", "WARNING") as logged:
            await self.power.stop_all()
        self.assertEqual(self.calls[2:], ["broken stop", "lamp stop"])
        self.assertIn("plugin broken: stop failed: RuntimeError: socket stuck", logged.output[0])

    async def test_a_switched_off_plugin_s_connection_isn_t_started_with_the_toolbox(self) -> None:
        self.switches.switch("lamp", False)
        await self.connections.start_all()
        self.assertEqual(self.lamp.calls, [])

    def test_an_id_that_is_no_loaded_plugin_is_never_off(self) -> None:
        self.switches.switch("gone", False)
        self.assertFalse(self.power.is_off("gone"))
        self.assertEqual(self.power.why_not("gone.box"), "")


if __name__ == "__main__":
    unittest.main()
