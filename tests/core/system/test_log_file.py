import logging
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.system.log_file import LogFile


class TestLogFile(unittest.TestCase):
    """His 11-20: what the toolbox says is kept in a file, a few MB at most, and Settings → Log shows it."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "logs"
        self.logger = logging.getLogger(f"test_log_file.{id(self)}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

    def tearDown(self) -> None:
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)
        self._dir.cleanup()

    def test_lines_go_into_the_file_with_their_time(self) -> None:
        log_file = LogFile(self.folder)
        log_file.attach(self.logger)
        self.logger.info("Twitch: connected")
        self.logger.warning("GET /toolbox/media/x.png answered 404")
        entries = log_file.entries()
        self.assertEqual(2, len(entries))
        self.assertRegex(entries[0], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ INFO .*: Twitch: connected$")
        self.assertIn(" WARNING ", entries[1])

    def test_a_traceback_stays_with_its_entry_and_the_filter_keeps_warnings_and_up(self) -> None:
        log_file = LogFile(self.folder)
        log_file.attach(self.logger)
        self.logger.info("fine")
        try:
            raise ValueError("broken")
        except ValueError:
            self.logger.exception("GET /x failed")
        self.logger.warning("careful")
        bad = log_file.entries(least="WARNING")
        self.assertEqual(2, len(bad))
        self.assertIn("Traceback", bad[0])
        self.assertIn("ValueError: broken", bad[0])
        self.assertTrue(bad[1].endswith("careful"))

    def test_a_full_file_becomes_an_old_one_and_the_folder_stays_small(self) -> None:
        log_file = LogFile(self.folder, most_bytes=2000, old_files=2)
        log_file.attach(self.logger)
        for number in range(200):
            self.logger.info("line %03d %s", number, "x" * 40)
        names = sorted(p.name for p in self.folder.iterdir())
        self.assertEqual(["toolbox.log", "toolbox.log.1", "toolbox.log.2"], names)
        self.assertTrue(all(p.stat().st_size <= 2000 for p in self.folder.iterdir()))
        # too few in the current file: the one before it is read too, the order stays
        entries = log_file.entries(count=30)
        self.assertEqual(30, len(entries))
        self.assertTrue(entries[-1].endswith("line 199 " + "x" * 40))
        numbers = [int(entry.split("line ")[1][:3]) for entry in entries]
        self.assertEqual(list(range(170, 200)), numbers)  # from all three files

    def test_no_file_yet_means_no_entries(self) -> None:
        self.assertEqual([], LogFile(self.folder).entries())
