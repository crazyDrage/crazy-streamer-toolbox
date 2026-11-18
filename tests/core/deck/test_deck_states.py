import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.deck.deck_button import DeckButton
from streamer_toolbox.core.deck.deck_states import DeckStates


class TestDeckStates(unittest.TestCase):
    """His 11-18: `"active": true` as a flow output sets the button's look, and it stays after a restart."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "live_states.json"
        self.followed = {("mic", "active")}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _states(self) -> DeckStates:
        return DeckStates(self.path, lambda: self.followed)

    def test_a_button_follows_the_latest_value_of_its_flows_output(self) -> None:
        states = self._states()
        button = DeckButton("Mic", "flow.mic", state="active")
        self.assertFalse(states.is_on(button))  # never heard: off
        states.heard("mic", {"active": True})
        self.assertTrue(states.is_on(button))
        self.assertEqual(states.version, 1)
        states.heard("mic", {"other": 1})  # another output keeps the state
        self.assertTrue(states.is_on(button))
        states.heard("mic", {"active": "false"})
        self.assertFalse(states.is_on(button))
        states.heard("mic", {})  # nothing given: nothing new
        self.assertEqual(states.version, 3)

    def test_without_a_state_or_not_a_flow_it_is_never_on(self) -> None:
        states = self._states()
        states.heard("mic", {"active": True})
        self.assertFalse(states.is_on(DeckButton("Mic", "flow.mic")))
        self.assertFalse(states.is_on(DeckButton("Mic", "obs.mute", state="active")))

    def test_it_stays_after_a_restart(self) -> None:
        self._states().heard("mic", {"active": True})
        button = DeckButton("Mic", "flow.mic", state="active")
        self.assertTrue(self._states().is_on(button))  # a new toolbox start reads the file
        restarted = self._states()
        restarted.heard("mic", {"active": 0})
        self.assertFalse(self._states().is_on(button))

    def test_only_followed_outputs_are_written_and_only_when_they_change(self) -> None:
        states = self._states()
        states.heard("chat", {"emoji_dict": {"Kappa": "big"}})  # no button follows it
        self.assertFalse(self.path.exists())
        states.heard("mic", {"active": "yes", "emoji_dict": {"x": 1}})
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"mic": {"active": True}})
        self.path.unlink()
        states.heard("mic", {"active": "on"})  # still on: not written again
        self.assertFalse(self.path.exists())

    def test_a_broken_file_means_everything_off(self) -> None:
        self.path.write_text("{not json", encoding="utf-8")
        self.assertFalse(self._states().is_on(DeckButton("Mic", "flow.mic", state="active")))

    def test_what_means_on(self) -> None:
        for value in (True, 1, 2.5, "true", "on", "yes", "1", "active", [1]):
            self.assertTrue(DeckStates.means_on(value), value)
        for value in (False, 0, 0.0, None, "", " false ", "OFF", "no", "0", "none", "null", []):
            self.assertFalse(DeckStates.means_on(value), value)
