import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import EventValue


class TestEventTypeStore(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "event_types.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_new_toolbox_has_the_default_types_hidden(self) -> None:
        store = EventTypeStore(self.path)
        self.assertEqual([t.name for t in store.all()],
                         ["chat", "chat_deleted", "follow", "sub", "resub", "gift", "cheer", "raid", "tip", "redeem",
                          "community_gift", "superchat", "member", "charity", "merch"])
        self.assertTrue(all(t.default and t.hidden for t in store.all()))
        self.assertEqual(store.get("follow").value("user").also_known_as, ("name",))

    def test_a_deleted_default_stays_gone_and_a_new_one_comes_once(self) -> None:
        EventTypeStore(self.path).delete("tip")
        self.assertIsNone(EventTypeStore(self.path).get("tip"))
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["defaults_added"].remove("raid")  # as if raid came with a later version
        data["types"] = [t for t in data["types"] if t["name"] != "raid"]
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(EventTypeStore(self.path).all()[-1].name, "raid")
        self.assertIsNone(EventTypeStore(self.path).get("tip"))

    def test_other_names_go_only_to_a_default_type_and_only_once(self) -> None:
        store = EventTypeStore(self.path)
        store.save("chat_deleted", replace(store.get("chat_deleted"), also_known_as=("delete-message",)))
        self.assertEqual(store.add_other_names("chat_deleted", ("delete-messages",)), ["delete-messages"])
        self.assertEqual(EventTypeStore(self.path).get("chat_deleted").also_known_as,
                         ("delete-message", "delete-messages"))
        self.assertEqual(store.add_other_names("chat_deleted", ("delete-messages",)), [])
        own = store.add("own")
        self.assertEqual(store.add_other_names(own.name, ("x",)), [])  # his own type stays as he made it

    def test_his_own_type_is_kept_with_its_values(self) -> None:
        store = EventTypeStore(self.path)
        made = store.add("lizard")
        self.assertEqual(store.add("lizard").name, "lizard_2")
        changed = replace(made, values=(EventValue("displayColor", "#ff0000", "colour", ("color",)),),
                          also_known_as=("lizard-latest",))
        store.save("lizard", changed)
        again = EventTypeStore(self.path)
        self.assertEqual(again.get("lizard"), changed)
        self.assertFalse(again.get("lizard").hidden)
        self.assertEqual([t.name for t in again.known_as("lizard-latest")], ["lizard"])

    def test_a_rename_keeps_its_place_and_a_taken_name_is_refused(self) -> None:
        store = EventTypeStore(self.path)
        store.save("follow", replace(store.get("follow"), name="follower"))
        names = [t.name for t in EventTypeStore(self.path).all()]
        self.assertEqual(names.index("follower"), 2)
        with self.assertRaises(ValueError):
            store.save("follower", replace(store.get("follower"), name="sub"))
        with self.assertRaises(ValueError):
            store.save("follower", replace(store.get("follower"), name="no spaces"))

    def test_subscriber_latest_is_heard_as_sub_resub_and_gift(self) -> None:
        self.assertEqual([t.name for t in EventTypeStore(self.path).known_as("subscriber-latest")],
                         ["sub", "resub", "gift"])


if __name__ == "__main__":
    unittest.main()
