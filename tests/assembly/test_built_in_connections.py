import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.assembly.built_in_connections import BuiltInConnections
from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.mixitup_connection import MixItUpConnection
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.twitch_connection import TwitchConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.config.obs_config import ObsConfig
from streamer_toolbox.core.event_types.default_event_types import DEFAULTS
from streamer_toolbox.core.event_types.event_flows import TRIGGERS
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe


class TestBuiltInConnections(unittest.TestCase):
    """What assemble() does with them at every start, without the GUI: build them all, then add their boxes the
    same way (add_actions, then boxes()). Nothing connects."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        events = EventBus()
        tokens = OAuthTokenStore(folder / "twitch_token.json")
        self.connections = BuiltInConnections({}, ObsConfig(), folder, events).build(
            Mp4HeaderProbe(), TwitchConnection({}, tokens, events), tokens, MixItUpConnection({}),
            HeartRate(events), lambda key: False, lambda: {})
        self.actions = ActionRegistry()
        for connection in self.connections:
            connection.add_actions(self.actions)
            for box in connection.boxes():
                self.actions.add_box(box, connection.id)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_every_connection_has_its_own_id(self) -> None:
        ids = [connection.id for connection in self.connections]
        self.assertEqual(len(ids), len(set(ids)), ids)

    def test_every_box_has_a_label_and_a_help_text(self) -> None:
        boxes = self.actions.all(include_flow_only=True)
        self.assertGreater(len(boxes), 150)  # the registry refuses a second box of the same name on its own
        self.assertEqual([b.name for b in boxes if not b.label or not b.description], [])

    def test_the_connections_with_boxes_bring_them(self) -> None:
        categories = {box.name.split(".")[0] for box in self.actions.all(include_flow_only=True)}
        for category in ("obs", "sammi", "mixitup", "vts", "twitch", "youtube", "streamerbot", "tits", "discord"):
            self.assertIn(category, categories)

    def test_the_events_of_add_default_flows_are_default_event_types_with_a_trigger(self) -> None:
        """His 11-14: "Add default flows" brings the connection's events and their flows (Twitch, YouTube)."""
        defaults = {kind.name for kind in DEFAULTS}
        offered = {connection.id: connection.event_types() for connection in self.connections}
        self.assertEqual(offered["youtube"], ("chat", "follow", "sub", "resub", "gift", "superchat", "member"))
        for connection_id, events in offered.items():
            self.assertEqual([e for e in events if e not in defaults or e not in TRIGGERS], [], connection_id)


if __name__ == "__main__":
    unittest.main()
