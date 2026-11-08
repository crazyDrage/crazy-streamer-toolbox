import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.deck.deck_button import DeckButton
from streamer_toolbox.core.deck.deck_page import DeckPage
from streamer_toolbox.core.exports.import_row import BOTH, NEW, REPLACE, SAME, SKIP, TAKEN
from streamer_toolbox.core.exports.toolbox_export import ToolboxExport
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.widgets.widget import Widget
from tests.fakes.toolbox_settings import ToolboxSettings


class TestExportImporter(unittest.TestCase):
    """His round 86: an export from one toolbox into another; a taken name is his choice."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.mine = ToolboxSettings(folder / "mine")
        self.theirs = ToolboxSettings(folder / "theirs")
        for rule in self.theirs.alerts.all():  # the alerts a new toolbox starts with
            self.theirs.alerts.delete(rule.id)
        picture = folder / "cheer.png"
        picture.write_bytes(b"png")
        self.picture = str(picture)
        self.mine.events.add("cheer")
        self.mine.alerts.save(AlertRule("cheer", "Cheer", on=True, image=self.picture, event="cheer"))
        self.mine.flows.save(Flow("thanks", "Thanks", (FlowNode("n1", "sound.play"),)))
        self.mine.flows.save(Flow("event_cheer", "Event: cheer", (
            FlowNode("n1", "event.send.cheer", {"only_to": "alert cheer"}), FlowNode("n2", "flow.thanks")),
            triggers=(FlowTrigger("cheer", {}, "t1"),)))
        self.mine.widgets.save(Widget("bar", js="// cheer", events=("cheer",)))
        self.mine.deck.save(Deck([DeckPage("Main", [DeckButton("Test cheer", "flow.event_cheer")])]))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _export(self) -> ToolboxExport:
        parts = self.mine.finder.connected([("alert", "cheer")], ticked={("widget", "bar"), ("button", "Main/0")})
        return ToolboxExport.from_bytes(self.mine.finder.export("Cheer set", parts).to_bytes())

    def test_into_an_empty_toolbox_everything_is_new_and_comes_in(self) -> None:
        export = self._export()
        states = {row.id: row.state for row in self.theirs.importer.rows(export)}
        self.assertEqual(SAME, states.pop(("event", "cheer")))  # a default event: every toolbox has it
        self.assertEqual({NEW}, set(states.values()))
        self.theirs.importer.run(export)
        rule = self.theirs.alerts.get("cheer")
        self.assertEqual(b"png", Path(rule.image).read_bytes())
        # in the settings folder: portable (the real folders compared: Windows may write one short, RUNNER~1)
        self.assertTrue(Path(rule.image).resolve().is_relative_to((self.theirs.folder / "media").resolve()))
        self.assertEqual("Event: cheer", self.theirs.flows.get("event_cheer").label)
        self.assertEqual(("cheer",), self.theirs.widgets.get("bar").events)
        self.assertIsNotNone(self.theirs.events.get("cheer"))
        self.assertEqual("flow.event_cheer", self.theirs.deck.load().page("Main").buttons[0].action)

    def test_the_same_toolbox_again_has_nothing_to_do(self) -> None:
        rows = self.mine.importer.rows(self._export())
        self.assertEqual({SAME}, {row.state for row in rows})

    def test_keep_both_renames_and_keeps_the_links(self) -> None:
        export = self._export()
        self.mine.flows.save(Flow("thanks", "Thanks", (FlowNode("n1", "sound.play", {"file": "other"}),)))
        self.mine.alerts.save(AlertRule("cheer", "Cheer", text="mine", event="cheer"))
        rows = {row.id: row for row in self.mine.importer.rows(export)}
        self.assertEqual((TAKEN, BOTH), (rows[("flow", "thanks")].state, rows[("flow", "thanks")].choice))
        self.mine.importer.run(export, {("alert", "cheer"): BOTH})
        new = self.mine.flows.get("event_cheer")  # the same as before: nothing to do
        self.assertEqual("flow.thanks", new.nodes[1].action)
        kept = self.mine.flows.get("thanks_2")
        self.assertEqual(("Thanks (imported)", ()), (kept.label, kept.triggers))
        alert = self.mine.alerts.get("cheer_2")
        self.assertEqual(("Cheer (imported)", False), (alert.name, alert.on))  # nothing plays twice
        self.assertEqual("mine", self.mine.alerts.get("cheer").text)

    def test_a_kept_both_flow_is_run_by_the_new_name_in_the_other_imported_flows(self) -> None:
        export = self._export()
        self.theirs.flows.save(Flow("thanks", "Theirs", ()))
        self.theirs.importer.run(export)
        self.assertEqual("flow.thanks_2", self.theirs.flows.get("event_cheer").nodes[1].action)
        self.assertEqual("Theirs", self.theirs.flows.get("thanks").label)

    def test_replace_and_skip(self) -> None:
        export = self._export()
        self.theirs.alerts.save(AlertRule("cheer", "Old"))
        self.theirs.flows.save(Flow("thanks", "Theirs", ()))
        self.theirs.importer.run(export, {("alert", "cheer"): REPLACE, ("flow", "thanks"): SKIP})
        self.assertEqual("Cheer", self.theirs.alerts.get("cheer").name)
        self.assertEqual("Theirs", self.theirs.flows.get("thanks").label)

    def test_needs_lists_what_cant_come_along(self) -> None:
        self.mine.flows.save(Flow("thanks", "Thanks", (FlowNode("n1", "plugin.lamp"),),
                                  triggers=(FlowTrigger("redeem", {"reward": "Hydrate"}, "t1"),)))
        needs = self.theirs.importer.needs(self._export())
        self.assertIn("The box plugin.lamp (a plugin or a connection this toolbox doesn't have)", needs)
        self.assertIn('The Twitch reward "Hydrate" (made on Twitch, it can\'t come along)', needs)

    def test_an_export_from_a_newer_toolbox_is_refused(self) -> None:
        export = self._export()
        export.settings_version = 999
        with self.assertRaisesRegex(ValueError, "newer toolbox"):
            self.theirs.importer.rows(export)


if __name__ == "__main__":
    unittest.main()
