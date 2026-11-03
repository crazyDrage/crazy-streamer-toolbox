import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.alerts.alert_input import AlertInput
from streamer_toolbox.core.alerts.alert_store import AlertStore


class TestAlertStore(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "alerts.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_new_toolbox_starts_with_the_usual_alerts_off_and_their_flows_to_make(self) -> None:
        store = AlertStore(self.path)
        self.assertEqual([r.title for r in store.all()],
                         ["Follow", "Sub", "Resub", "Gift subs", "Cheer", "Raid", "Tip"])
        self.assertFalse(any(r.on for r in store.all()))
        self.assertEqual([event for _, event in store.unstarted],
                         ["follow", "sub", "resub", "gift", "cheer", "raid", "tip"])
        store.started()
        self.assertEqual(AlertStore(self.path).unstarted, [])  # once

    def test_his_own_alerts_names_and_order_are_kept(self) -> None:
        store = AlertStore(self.path)
        rule = store.add("Lizard redeem", (AlertInput("user", example="Kit"), AlertInput("times", "number", "3", True)))
        self.assertEqual((rule.id, rule.text, rule.amount_input), ("lizard_redeem", "{user}", "times"))
        self.assertEqual(store.add("Lizard redeem").id, "lizard_redeem_2")
        store.save(replace(rule, name="Lizard!"))
        again = AlertStore(self.path)
        self.assertEqual([r.title for r in again.all()][-2:], ["Lizard!", "Lizard redeem"])
        self.assertEqual(again.get("lizard_redeem"), replace(rule, name="Lizard!"))
        again.delete("lizard_redeem")
        self.assertIsNone(AlertStore(self.path).get("lizard_redeem"))

    def test_the_file_from_before_round_65_becomes_his_list(self) -> None:
        """One alert per event then; its settings stay, it gets its event's inputs, and its flow is made."""
        self.path.write_text(json.dumps({"alerts": {
            "twitch.cheer": {"on": True, "text": "{user}: {bits} bits", "minimum": 50,
                             "pieces": [{"kind": "text"}, {"kind": "name", "on_picture": True, "x": 10}]},
            "twitch.sub": {"on": False, "image": "C:\\alerts\\card.png", "text": ""}},
            "keep_through_restart": True}), encoding="utf-8")
        store = AlertStore(self.path)
        cheer = store.get("cheer")
        self.assertEqual((cheer.title, cheer.on, cheer.text, cheer.minimum), ("Cheer", True, "{user}: {bits} bits", 50))
        self.assertEqual([i.name for i in cheer.inputs], ["user", "bits", "message"])  # named like cheer's values
        self.assertEqual(cheer.event, "cheer")
        self.assertEqual(cheer.parts[1].x, 10)
        self.assertEqual(cheer.alert_for({"user": "Kit", "bits": 100}).text, "Kit: 100 bits")
        self.assertEqual((store.get("sub").image, store.get("sub").text), ("C:\\alerts\\card.png", ""))
        self.assertEqual(store.get("follow").text, "{user} just followed!")  # not in the file: as it starts
        self.assertEqual(len(store.unstarted), 7)
        self.assertTrue(store.keep_through_restart)
        before = self.path.read_text(encoding="utf-8")
        store.started()
        self.assertEqual(self.path.with_name("alerts.before_round_65.json").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
