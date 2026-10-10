import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.widgets.widget_session import WidgetSession


class TestWidgetSession(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "cache" / "widget_session.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_latest_ones_are_there_again_after_a_restart(self) -> None:
        session = WidgetSession(self.path)
        session.add("follower-latest", {"type": "follower", "name": "Kit"})
        session.add("cheer-latest", {"type": "cheer", "name": "Vex", "amount": 100})
        again = WidgetSession(self.path)
        self.assertEqual((again.data["follower-latest"]["name"], again.data["cheer-total"]["amount"],
                          len(again.data["cheer-recent"]), len(again.recents)), ("Kit", 100, 1, 2))
        self.assertEqual(again.data["cheer-session"], {"count": 0, "amount": 0})  # this session starts at 0

    def test_without_a_file_nothing_is_kept(self) -> None:
        WidgetSession().add("follower-latest", {"type": "follower", "name": "Kit"})
        self.assertEqual(WidgetSession().data["follower-latest"]["name"], "")

    def test_a_broken_file_is_an_empty_start(self) -> None:
        self.path.parent.mkdir()
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(WidgetSession(self.path).data["follower-latest"]["name"], "")
        self.path.write_text('{"data": {"follower-latest": "text", "raid-recent": {}}}', encoding="utf-8")
        session = WidgetSession(self.path)
        self.assertEqual((session.data["follower-latest"]["name"], session.data["raid-recent"]), ("", []))


if __name__ == "__main__":
    unittest.main()
