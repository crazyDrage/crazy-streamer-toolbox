import asyncio
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_skipped import FlowSkipped
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowHidden(unittest.TestCase):
    """His "hide in list" (2026-10-29): a flow or a folder can be left out of the Flows page's list."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.library = self._library()

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _library(self) -> FlowLibrary:
        actions = ActionRegistry()
        library = FlowLibrary(FlowStore(self.folder / "flows"), FlowStore(self.folder / "templates"),
                              FlowRunner(actions, VariableStore(self.folder / "v.json")), actions)
        library.load()
        return library

    def test_a_hidden_flow_is_kept_hidden_and_still_runs(self) -> None:
        self.library.save(Flow("lizard", "Lizard", hidden=True))
        self.library.save(Flow("other", "Other"))
        again = self._library()
        self.assertEqual([f.name for f in again.all() if again.hidden(f)], ["lizard"])
        self.assertIn("flow.lizard", again._actions)  # it is still a box and runs
        again.save(replace(again.get("lizard"), hidden=False))
        self.assertFalse(self._library().hidden(self._library().get("lizard")))

    def test_a_hidden_folder_hides_its_flows_and_goes_along_when_renamed(self) -> None:
        self.library.save(Flow("follow", "Alert: Follow", folder="Alerts"))
        self.library.folder_settings.set_hidden("Alerts", True)
        again = self._library()
        self.assertTrue(again.hidden(again.get("follow")))
        again.rename_folder("Alerts", "My alerts")
        again = self._library()
        self.assertTrue(again.folder_settings.hidden("My alerts"))
        self.assertFalse(again.folder_settings.hidden("Alerts"))
        self.assertFalse(again.folder_settings.hidden(""))  # "no folder" is never hidden


    def test_a_switched_off_folder_starts_none_of_its_flows(self) -> None:
        """His "the flow folders need a disable button to disable the whole folder" (10-29)."""
        self.library.save(Flow("raid", "Raid", triggers=(FlowTrigger("raid", {}, "t1"),), folder="Alerts"))
        self.library.folder_settings.set_off("Alerts", True)
        again = self._library()
        with self.assertRaisesRegex(FlowSkipped, "folder 'Alerts'"):
            asyncio.run(again._actions.run("flow.raid"))
        started = []
        router = FlowTriggerRouter(again, again._runner)
        router._run = lambda flow, *_: started.append(flow.name) or asyncio.sleep(0)
        asyncio.run(router.handle("raid", {"user": "Big"}))
        self.assertEqual(started, [])
        again.folder_settings.set_off("Alerts", False)
        asyncio.run(router.handle("raid", {"user": "Big"}))
        self.assertEqual(started, ["raid"])
        self.assertTrue(again.get("raid").enabled)  # its own switch stays as it was


if __name__ == "__main__":
    unittest.main()
