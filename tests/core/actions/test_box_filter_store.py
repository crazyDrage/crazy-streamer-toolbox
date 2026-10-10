import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.box_filter import BoxFilter
from streamer_toolbox.core.actions.box_filter_store import BASIC_FILTERS, BoxFilterStore
from streamer_toolbox.core.actions.registered_action import RegisteredAction


async def noop() -> None:
    return None


class TestBoxFilterStore(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "box_filters.json"
        self.store = BoxFilterStore(self.path)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_filter_fits_whole_categories_and_single_groups(self) -> None:
        sound_job = BoxFilter("Sound job", ("sound", "obs/Audio"))
        self.assertTrue(sound_job.fits(RegisteredAction("sound.play", noop, "")))
        self.assertTrue(sound_job.fits(RegisteredAction("obs.set_volume", noop, "", group="Audio")))
        self.assertFalse(sound_job.fits(RegisteredAction("obs.switch_scene", noop, "", group="Scenes")))
        self.assertTrue(BoxFilter("x", ("logic/General",)).fits(RegisteredAction("logic.if", noop, "")))

    def test_his_own_come_after_the_basic_ones_and_are_kept(self) -> None:
        self.store.save(BoxFilter(" Alerts ", ("obs/Media", "sound", "logic.wait"), ("obs.get_media_status",)))
        self.assertEqual([f.name for f in self.store.all()], [*(f.name for f in BASIC_FILTERS), "Alerts"])
        again = BoxFilterStore(self.path)
        self.assertEqual(again.custom(), [BoxFilter("Alerts", ("obs/Media", "sound", "logic.wait"),
                                                    ("obs.get_media_status",))])
        alerts = again.get("Alerts")
        self.assertTrue(alerts.fits(RegisteredAction("logic.wait", noop, "")))  # one single box
        self.assertTrue(alerts.fits(RegisteredAction("obs.play_video_once", noop, "", group="Media")))
        self.assertFalse(alerts.fits(RegisteredAction("obs.get_media_status", noop, "", group="Media")))
        self.assertEqual(again.get("alerts").parts, ("obs/Media", "sound", "logic.wait"))

    def test_edit_rename_and_delete(self) -> None:
        self.store.save(BoxFilter("Alerts", ("sound",)))
        self.store.save(BoxFilter("Lizard", ("var",)))
        self.store.save(BoxFilter("Sound alerts", ("sound", "obs")), old_name="Alerts")
        self.assertEqual([f.name for f in self.store.custom()], ["Sound alerts", "Lizard"])  # keeps its place
        self.store.delete("lizard")
        self.assertEqual([f.name for f in BoxFilterStore(self.path).custom()], ["Sound alerts"])

    def test_names_are_unique_and_a_filter_shows_something(self) -> None:
        self.store.save(BoxFilter("Alerts", ("sound",)))
        with self.assertRaisesRegex(ValueError, "'Alerts' already"):
            self.store.save(BoxFilter("alerts", ("obs",)))
        with self.assertRaisesRegex(ValueError, "'Basics' already"):
            self.store.save(BoxFilter("basics", ("obs",)))
        with self.assertRaisesRegex(ValueError, "needs a name"):
            self.store.save(BoxFilter(" ", ("obs",)))
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.store.save(BoxFilter("Empty"))


if __name__ == "__main__":
    unittest.main()
