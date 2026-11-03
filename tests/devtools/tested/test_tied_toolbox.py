import sys
import threading
import unittest

from streamer_toolbox.devtools.tested.tied_toolbox import TiedToolbox

# stands in for a toolbox started with --tied: runs until its stdin ends
UNTIL_STDIN_ENDS = [sys.executable, "-c", "import sys; sys.stdin.buffer.read()"]


class TestTiedToolbox(unittest.TestCase):
    def test_stop_ends_it_and_isnt_taken_for_it_going_by_itself(self) -> None:
        gone = threading.Event()
        tied = TiedToolbox(UNTIL_STDIN_ENDS, stop_wait=10)
        tied.start(gone.set)
        tied.stop()
        self.assertEqual(tied._process.poll(), 0)
        self.assertFalse(gone.wait(0.3))

    def test_it_ending_by_itself_stops_the_test_window_too(self) -> None:
        gone = threading.Event()
        TiedToolbox([sys.executable, "-c", "pass"]).start(gone.set)  # its app window was closed
        self.assertTrue(gone.wait(10))

    def test_one_that_doesnt_stop_is_killed(self) -> None:
        tied = TiedToolbox([sys.executable, "-c", "import time; time.sleep(30)"], stop_wait=0.5)
        tied.start(lambda: None)
        tied.stop()
        self.assertIsNotNone(tied._process.poll())


if __name__ == "__main__":
    unittest.main()
