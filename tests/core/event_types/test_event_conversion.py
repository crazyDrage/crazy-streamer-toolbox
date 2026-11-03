import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_conversion import ALERTS_BEFORE, EventConversion
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.events_upgrade import EventsUpgrade
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.upgrades.settings_upgrades import SettingsUpgrades
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class TestEventConversion(unittest.TestCase):
    """His answer 2 a: what widgets and alerts had before round 78 becomes events, once, the old file kept."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.events = EventTypeStore(self.folder / "event_types.json")
        self.widgets = WidgetStore(self.folder / "widgets")
        actions = ActionRegistry()
        self.flows = FlowLibrary(FlowStore(self.folder / "flows"), FlowStore(self.folder / "templates"),
                                 FlowRunner(actions, VariableStore(self.folder / "variables.json")), actions)
        self.flows.load()

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _round_74_widget(self) -> None:
        self.widgets.save(Widget("goal"))
        (self.folder / "widgets" / "goal" / "inputs.json").write_text(json.dumps([
            {"name": "follow", "kind": "follow", "listener": "new-follower"},
            {"name": "progress", "kind": "custom", "fields": "done, goal"}]), encoding="utf-8")

    def _round_65_alerts(self) -> AlertStore:
        (self.folder / "alerts.json").write_text(json.dumps({"alerts": [
            {"id": "cheer", "name": "Cheer", "inputs": [{"name": "user"}, {"name": "amount", "kind": "number",
                                                                           "amount": True}],
             "text": "{user} cheered {amount}!", "pieces": [{"kind": "text"}]},
            {"id": "lizard", "name": "Lizard", "inputs": [{"name": "times", "kind": "number", "example": "3"}],
             "text": "{times} lizards", "pieces": [{"kind": "text"}]}]}), encoding="utf-8")
        return AlertStore(self.folder / "alerts.json")

    def test_widget_inputs_become_events(self) -> None:
        self._round_74_widget()
        alerts = AlertStore(self.folder / "alerts.json")
        EventConversion(self.events, self.widgets, alerts, self.flows).run()
        self.assertEqual(self.widgets.get("goal").events, ("follow", "progress"))
        self.assertIn("new-follower", self.events.get("follow").also_known_as)
        self.assertEqual([v.name for v in self.events.get("progress").values], ["done", "goal"])
        self.assertEqual(EventConversion(self.events, self.widgets, alerts, self.flows).run(), [])  # once

    def test_alerts_get_their_event_and_the_old_file_is_kept(self) -> None:
        alerts = self._round_65_alerts()
        before = (self.folder / "alerts.json").read_text(encoding="utf-8")
        EventConversion(self.events, self.widgets, alerts, self.flows).run()
        cheer = alerts.get("cheer")
        self.assertEqual((cheer.event, [i.name for i in cheer.inputs], cheer.amount_input),
                         ("cheer", ["user", "bits"], "bits"))
        self.assertEqual(cheer.alert_for({"user": "Kit", "bits": 5}).text, "Kit cheered 5!")
        lizard = alerts.get("lizard")
        self.assertEqual((lizard.event, self.events.get("lizard").values[0].default), ("lizard", "3"))
        self.assertEqual((self.folder / ALERTS_BEFORE).read_text(encoding="utf-8"), before)

    def test_their_boxes_in_flows_become_send_boxes_to_that_one_only(self) -> None:
        self._round_74_widget()
        alerts = self._round_65_alerts()
        self.flows.save(Flow("old", "Old", (FlowNode("n1", "alert.play.cheer", {"user": "x", "amount": "5"}),
                                            FlowNode("n2", "widget.send.goal.progress", {"done": "1"}))))
        EventConversion(self.events, self.widgets, alerts, self.flows).run()
        cheer, goal = self.flows.get("old").nodes
        self.assertEqual((cheer.action, cheer.params), ("event.send.cheer",
                                                        {"user": "x", "bits": "5", "only_to": "alert cheer"}))
        self.assertEqual((goal.action, goal.params), ("event.send.progress", {"done": "1", "only_to": "widget goal"}))
        self.assertTrue(self.events.flow_made("cheer"))  # sent already: no flow of its own on top

    def test_an_alerts_own_box_found_later_becomes_a_send_box(self) -> None:
        """His answer 2 b: the alerts' own boxes are gone; one in a flow brought in later still works."""
        alerts = AlertStore(self.folder / "alerts.json")  # a new toolbox: its alerts have their events
        self.flows.save(Flow("imported", "Imported", (FlowNode("n1", "alert.play.follow", {"user": "x"}),)))
        EventConversion(self.events, self.widgets, alerts, self.flows).run()
        node = self.flows.get("imported").nodes[0]
        self.assertEqual((node.action, node.params), ("event.send.follow", {"user": "x", "only_to": "alert follow"}))

    def test_an_old_export_is_upgraded_on_import_and_a_new_one_says_its_version(self) -> None:
        """His next release plan, part 3: exports carry the settings version; an older one is upgraded."""
        alerts = AlertStore(self.folder / "alerts.json")
        conversion = EventConversion(self.events, self.widgets, alerts, self.flows)
        self.flows.upgrade = SettingsUpgrades(self.folder / "toolbox.toml", [EventsUpgrade(conversion)]).flow
        old = 'label = "Old"\n[[nodes]]\nid = "n1"\naction = "alert.play.follow"\nparams = { user = "x" }\n'
        node = self.flows.import_file(old, "old.toml")[0].nodes[0]
        self.assertEqual((node.action, node.params), ("event.send.follow", {"user": "x", "only_to": "alert follow"}))
        pack = FlowPack("Old", (Flow("p", "P", (FlowNode("n1", "alert.play.raid", {}),)),), settings_version=0)
        self.assertEqual(self.flows.import_pack(pack)[0].nodes[0].action, "event.send.raid")
        self.assertIn("settings_version = 1", self.flows.export_text(self.flows.all()[0].name))
        self.assertIn("settings_version = 1", self.flows.folder_pack("Old").to_text())
        with self.assertRaisesRegex(ValueError, "newer toolbox"):
            self.flows.import_file("settings_version = 99\n" + old, "new.toml")


if __name__ == "__main__":
    unittest.main()
