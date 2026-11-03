import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _output_ends_within(seconds: float, *arguments: str) -> bool:
    """Runs tests.helpers.tied_launch_once: True when its stdout (which the program it started holds too) ends
    within `seconds`, i.e. that program is gone with it."""
    helper = subprocess.Popen([sys.executable, "-m", "tests.helpers.tied_launch_once", *arguments], cwd=REPO,
                              stdout=subprocess.PIPE,
                              env={**os.environ, "PYTHONPATH": os.pathsep.join(("src", "."))})
    ended = threading.Event()

    def read() -> None:
        helper.stdout.read()
        ended.set()

    threading.Thread(target=read, daemon=True).start()
    result = ended.wait(seconds)
    helper.wait(10)
    if result:
        helper.stdout.close()
    return result


@unittest.skipUnless(sys.platform == "win32" or sys.platform.startswith("linux"), "Windows and Linux only")
class TestTiedLaunch(unittest.TestCase):
    def test_what_it_starts_ends_when_the_starter_ends_without_clean_up(self) -> None:
        self.assertTrue(_output_ends_within(10))

    def test_a_plain_start_would_outlive_it(self) -> None:  # the check above can tell the two apart
        self.assertFalse(_output_ends_within(3, "plain"))


if __name__ == "__main__":
    unittest.main()
