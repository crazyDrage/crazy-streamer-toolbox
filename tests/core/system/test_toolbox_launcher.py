import unittest

from streamer_toolbox.core.interfaces.page_opener import PageOpener
from streamer_toolbox.core.system.toolbox_launcher import ToolboxLauncher
from streamer_toolbox.core.system.toolbox_restart import RESTART_EXIT_CODE
from tests.fakes.fake_child_process import FakeChildProcess
from tests.fakes.fake_page_opener import FakePageOpener


class TestToolboxLauncher(unittest.TestCase):
    def _launcher(self, codes: list[int], opener: PageOpener | None = None) -> tuple[ToolboxLauncher, list]:
        started: list[FakeChildProcess] = []

        def launch(command, stdin=None):
            started.append(FakeChildProcess(codes[len(started)]))
            return started[-1]

        return ToolboxLauncher(["toolbox"], "http://127.0.0.1:8850", opener, launch, ready=lambda url: True), started

    def test_starts_it_again_on_restart_and_opens_the_page_only_once(self) -> None:
        opener = FakePageOpener()
        launcher, started = self._launcher([RESTART_EXIT_CODE, RESTART_EXIT_CODE, 0], opener)
        self.assertEqual(launcher.run(), 0)
        self.assertEqual(len(started), 3)
        self.assertEqual(opener.opened, ["http://127.0.0.1:8850"])

    def test_gives_back_a_failure_code_without_starting_again(self) -> None:
        launcher, started = self._launcher([1])
        self.assertEqual(launcher.run(), 1)
        self.assertEqual(len(started), 1)

    def test_stop_closes_the_childs_stdin_and_a_restart_code_then_ends_it(self) -> None:
        launcher, started = self._launcher([RESTART_EXIT_CODE, 0])
        launcher._child = FakeChildProcess(0)
        launcher.stop()  # the window was closed
        self.assertTrue(launcher._child.stdin.closed)
        self.assertEqual(launcher.run(), RESTART_EXIT_CODE)
        self.assertEqual(len(started), 1)


if __name__ == "__main__":
    unittest.main()
