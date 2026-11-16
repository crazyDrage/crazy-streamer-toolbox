import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.cache.remembered_values import MONTH, RememberedValues, own_group


class TestRememberedValues(unittest.TestCase):
    """His round 90: values kept a while under a name, per group with its own most count, also after a restart;
    nothing forever (no max age = a month)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "cache" / "remembered_values.json"
        self.now = 1000.0
        self.values = RememberedValues(self.path, clock=lambda: self.now)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_found_while_younger_than_the_max_age(self) -> None:
        self.values.set("pfp", "twitch:11", "/kit.png", 600, 100)
        self.now += 599
        self.assertEqual((True, "/kit.png", 599), self.values.get("pfp", "twitch:11", 600))
        self.assertFalse(self.values.get("pfp", "twitch:11", 60)[0])  # a box asking for younger ones
        self.now += 2
        self.assertFalse(self.values.get("pfp", "twitch:11", 600)[0])
        self.assertEqual((False, None, 0.0), self.values.get("pfp", "nobody", 600))

    def test_kept_through_a_restart_and_too_old_ones_go(self) -> None:
        self.values.set("pfp", "a", {"url": "x", "n": 2}, 60, 100)
        self.values.set("pfp", "b", "y", 0, 100)  # no max age: a month
        self.now += 61
        again = RememberedValues(self.path, clock=lambda: self.now)
        self.assertEqual(1, again.count("pfp"))
        self.assertEqual((True, "y", 61), again.get("pfp", "b", 0))
        self.now += MONTH
        self.assertEqual(0, RememberedValues(self.path, clock=lambda: self.now).count("pfp"))

    def test_a_full_group_drops_the_one_unused_the_longest_other_groups_keep_theirs(self) -> None:
        for key in ("a", "b", "c"):
            self.values.set("pfp", key, key, 600, 3)
            self.now += 100
        self.values.set("other", "z", "z", 600, 1)
        self.values.get("pfp", "a", 600)  # used again: b is the longest unused now
        self.values.set("pfp", "d", "d", 600, 3)
        self.assertEqual([True, False, True, True], [self.values.get("pfp", k, 600)[0] for k in "abcd"])
        self.assertTrue(self.values.get("other", "z", 600)[0])

    def test_a_box_gone_from_its_flow_takes_its_own_group(self) -> None:
        self.values.set(own_group("chat", "n5"), "k", 1, 60, 10)
        self.values.set("shared", "k", 1, 60, 10)
        self.values.forget("chat", ["n5"])
        self.assertEqual((0, 1), (self.values.count(own_group("chat", "n5")), self.values.count("shared")))
        self.assertNotIn(own_group("chat", "n5"), json.loads(self.path.read_text(encoding="utf-8")))

    def test_a_broken_file_is_no_loss(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertLogs("streamer_toolbox.core.cache.remembered_values", "WARNING"):
            self.assertEqual(0, RememberedValues(self.path).count("pfp"))


if __name__ == "__main__":
    unittest.main()
