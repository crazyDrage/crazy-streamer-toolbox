import unittest

from streamer_toolbox.gui.services.activity_log import ActivityLog


class TestActivityLog(unittest.TestCase):
    def test_newest_first_and_capped(self) -> None:
        log = ActivityLog(size=2)
        log.add("GUI", "a", True, None)
        log.add("sammi", "b", True, {"fitted": True})
        log.add("kit", "c", False, ValueError("boom"))
        self.assertEqual([(e.source, e.action, e.ok, e.text) for e in log.entries()],
                         [("kit", "c", False, "boom"), ("sammi", "b", True, "{'fitted': True}")])
        self.assertEqual(log.version, 3)

    def test_none_result_reads_done(self) -> None:
        log = ActivityLog()
        log.add("GUI", "a", True, None)
        self.assertEqual(log.entries()[0].text, "done")


if __name__ == "__main__":
    unittest.main()
