import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_skipped import FlowSkipped
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft


class TestFlowSwitches(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.actions, self.calls, self.reports = ActionRegistry(), [], []

        async def record() -> None:
            self.calls.append("ran")

        self.actions.add("a.record", record)
        self.runner = FlowRunner(self.actions, VariableStore(folder / "v.json"))
        self.store = FlowStore(folder / "flows")
        self.library = FlowLibrary(self.store, FlowStore(folder / "t"), self.runner, self.actions)
        self.flow = Flow("hug", "Hug", (FlowNode("n1", "a.record"),), (FlowWire("start", "out", "n1"),),
                         (FlowTrigger("twitch.redeem", {"reward": "Hug"}),))
        self.bus = EventBus()
        self.bus.subscribe(FlowTriggerRouter(self.library, self.runner, lambda *e: self.reports.append(e)).handle)

    async def asyncTearDown(self) -> None:
        self._dir.cleanup()

    async def _redeem(self) -> None:
        self.bus.publish("twitch.redeem", {"reward": "Hug", "user": "Kit"})
        await self.bus.wait_idle()

    async def test_triggers_off_its_triggers_are_quiet_and_its_button_still_runs_it(self) -> None:
        self.library.save(replace(self.flow, triggers_enabled=False))
        await self._redeem()
        self.assertEqual((self.calls, self.reports), ([], []))  # nothing started, nothing to report
        await self.actions.run("flow.hug")
        self.assertEqual(self.calls, ["ran"])

    async def test_flow_off_nothing_starts_it_and_a_start_says_why(self) -> None:
        self.library.save(replace(self.flow, enabled=False))
        await self._redeem()
        self.assertEqual((self.calls, self.reports), ([], []))
        with self.assertRaisesRegex(FlowSkipped, "'Hug' is switched off"):
            await self.actions.run("flow.hug")
        results, error = await self.runner.test_run(self.library.get("hug"))  # the editor's Test run still works
        self.assertEqual((len(results), error, self.calls), (1, None, ["ran"]))
        self.library.save(self.flow)  # switched on again
        await self._redeem()
        self.assertEqual(self.calls, ["ran", "ran"])

    def test_the_switches_are_kept_in_the_file_and_only_said_when_off(self) -> None:
        self.assertNotIn("enabled", FlowStore.to_data(self.flow))
        off = replace(self.flow, enabled=False, triggers_enabled=False)
        data = FlowStore.to_data(off)
        self.assertEqual((data["enabled"], data["triggers_enabled"]), (False, False))
        self.store.save(off)
        loaded = next(f for f in self.store.all() if f.name == "hug")
        self.assertEqual((loaded.enabled, loaded.triggers_enabled), (False, False))
        self.assertEqual(FlowDraft.from_flow(loaded).to_flow(), loaded)  # the editor keeps them
        self.assertTrue(FlowStore.parse("old", {"label": "Old"}).enabled)  # a flow from before is on


if __name__ == "__main__":
    unittest.main()
