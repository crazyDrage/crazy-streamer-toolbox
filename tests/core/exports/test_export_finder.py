import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.deck.deck_button import DeckButton
from streamer_toolbox.core.deck.deck_page import DeckPage
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.widgets.widget import Widget
from tests.fakes.toolbox_settings import ToolboxSettings


class TestExportFinder(unittest.TestCase):
    """His round 86: an export with everything connected (alert → event → its flow → what that flow uses)."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.box = ToolboxSettings(folder / "toolbox")
        self.picture = folder / "cheer.png"
        self.picture.write_bytes(b"png")
        self.sound = folder / "ding.mp3"
        self.sound.write_bytes(b"mp3")
        self.box.events.add("cheer")
        self.box.alerts.save(AlertRule("cheer", "Cheer", image=str(self.picture), event="cheer"))
        self.box.variables.set("cheers", 3)
        self.box.flows.save(Flow("thanks", "Thanks", (FlowNode("n1", "sound.play", {"file": str(self.sound)}),)))
        self.box.flows.save(Flow("event_cheer", "Event: cheer", (
            FlowNode("n1", "event.send.cheer", {"user": "${var.cheers}"}), FlowNode("n2", "flow.thanks"))))
        self.box.widgets.save(Widget("bar", js="// cheer", events=("cheer",)))
        self.box.deck.save(Deck([DeckPage("Main", [DeckButton("Test cheer", "flow.event_cheer")])]))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_an_alert_brings_its_event_the_flow_that_sends_it_and_what_that_flow_uses(self) -> None:
        parts = {p.id: p for p in self.box.finder.connected([("alert", "cheer")])}
        ticked = {key for key, part in parts.items() if part.ticked}
        self.assertEqual({("alert", "cheer"), ("event", "cheer"), ("flow", "event_cheer"), ("flow", "thanks"),
                          ("variable", "cheers")}, ticked)
        self.assertFalse(parts[("widget", "bar")].ticked)  # offered: it also gets cheer
        self.assertFalse(parts[("button", "Main/0")].ticked)
        self.assertEqual("sends the event cheer", parts[("flow", "event_cheer")].why)

    def test_an_offered_part_he_ticks_is_followed_and_one_he_unticks_is_not(self) -> None:
        parts = {p.id: p for p in self.box.finder.connected([("alert", "cheer")], ticked={("widget", "bar")},
                                                             unticked={("flow", "event_cheer")})}
        self.assertTrue(parts[("widget", "bar")].ticked)
        self.assertFalse(parts[("flow", "event_cheer")].ticked)
        self.assertNotIn(("flow", "thanks"), parts)

    def test_the_export_carries_the_files_and_a_widgets_folder(self) -> None:
        parts = self.box.finder.connected([("alert", "cheer")], ticked={("widget", "bar")})
        export = self.box.finder.export("Cheer", parts)
        entries = {(e["kind"], e["key"]): e for e in export.entries}
        alert_files = entries[("alert", "cheer")]["files"]
        self.assertEqual(b"png", export.files[alert_files[str(self.picture)]])
        self.assertEqual(b"mp3", export.files[entries[("flow", "thanks")]["files"][str(self.sound)]])
        self.assertEqual(b"// cheer", export.files["widgets/bar/widget.js"])
        self.assertNotIn(("button", "Main/0"), entries)

    def test_nothing_from_secrets_goes_along(self) -> None:
        secrets = self.box.folder / "secrets"
        secrets.mkdir()
        (secrets / "twitch.json").write_text("token")
        export = self.box.finder.export("All", self.box.finder.connected(
            [("alert", "cheer"), ("widget", "bar"), ("flow", "thanks")]))
        self.assertFalse([name for name in export.files if "secrets" in name])
        self.assertNotIn(b"token", export.to_bytes())

    def test_a_widget_value_without_a_field_stays_home(self) -> None:
        folder = self.box.folder / "widgets" / "bar"
        (folder / "fields.json").write_text('{"color": {"type": "colorpicker"}}')
        (folder / "values.json").write_text('{"color": "red", "token": "secret"}')
        export = self.box.finder.export("Bar", self.box.finder.connected([("widget", "bar")]))
        self.assertEqual({"color": "red"}, json.loads(export.files["widgets/bar/values.json"]))
        self.assertNotIn(b"secret", export.to_bytes())


if __name__ == "__main__":
    unittest.main()
