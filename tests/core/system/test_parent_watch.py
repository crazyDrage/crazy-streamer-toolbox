import os
import unittest

from streamer_toolbox.core.system.parent_watch import ParentWatch


class TestParentWatch(unittest.TestCase):
    def test_stops_the_toolbox_when_the_launcher_closes_stdin(self) -> None:
        read, write = os.pipe()
        gone = []
        thread = ParentWatch(read, lambda: gone.append(True)).start()
        os.write(write, b"anything")
        thread.join(0.2)
        self.assertEqual(gone, [])  # still there
        os.close(write)  # the window was closed
        thread.join(2)
        os.close(read)
        self.assertEqual(gone, [True])

    def test_a_closed_descriptor_counts_as_gone(self) -> None:
        read, write = os.pipe()
        os.close(write)
        os.close(read)
        gone = []
        ParentWatch(read, lambda: gone.append(True)).start().join(2)
        self.assertEqual(gone, [True])


if __name__ == "__main__":
    unittest.main()
