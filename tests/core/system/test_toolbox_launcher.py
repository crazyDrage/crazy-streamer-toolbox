import unittest

from streamer_toolbox.core.interfaces.page_opener import PageOpener
from streamer_toolbox.core.system.toolbox_launcher import ToolboxLauncher
from streamer_toolbox.core.system.toolbox_restart import RESTART_EXIT_CODE
from streamer_toolbox.core.system.update_starter import UPDATE_EXIT_CODE
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

    def test_gives_up_after_three_quick_restarts_in_a_row(self) -> None:
        # 11-03: a toolbox that couldn't start (exit 3, then the restart code) was started again forever
        launcher, started = self._launcher([RESTART_EXIT_CODE] * 5 + [0])
        self.assertEqual(launcher.run(), RESTART_EXIT_CODE)
        self.assertEqual(len(started), 3)

    def test_gives_back_a_failure_code_without_starting_again(self) -> None:
        launcher, started = self._launcher([1])
        self.assertEqual(launcher.run(), 1)
        self.assertEqual(len(started), 1)

    def test_stop_closes_the_childs_stdin_and_a_restart_code_then_ends_it(self) -> None:
        launcher, started = self._launcher([RESTART_EXIT_CODE, 0])
        launcher._child = FakeChildProcess(0)
        launcher.stop()  # the window was closed
        self.assertTrue(launcher._child.stdin.closed)
        launcher, started = self._launcher([RESTART_EXIT_CODE, 0])
        opener = FakePageOpener()
        launcher._opener = opener
        launcher._ready = lambda url: (launcher.stop(), True)[1]  # stopped while it runs
        self.assertEqual(launcher.run(), RESTART_EXIT_CODE)
        self.assertEqual(len(started), 1)
        self.assertTrue(started[0].stdin.closed)

    def test_restart_from_outside_starts_it_again_whatever_its_code(self) -> None:
        launcher, started = self._launcher([0, 0], FakePageOpener())  # the opener's wait is where it runs
        launcher._ready = lambda url: (launcher.restart(), True)[1] if len(started) == 1 else True
        self.assertEqual(launcher.run(), 0)
        self.assertEqual(len(started), 2)  # the starter's Restart: ended with 0, started again once
        self.assertTrue(started[0].stdin.closed)

    def test_stopped_before_it_started_starts_nothing(self) -> None:
        """--tied: the program that started it may be gone before the toolbox is (TiedToolbox)."""
        launcher, started = self._launcher([0])
        launcher.stop()
        self.assertEqual(launcher.run(), 0)
        self.assertEqual(started, [])

    def test_an_update_ends_the_launcher_once_the_swap_runs(self) -> None:
        """His next release plan, part 1: nothing may hold the old files while they are replaced."""
        started: list[FakeChildProcess] = []
        codes = [UPDATE_EXIT_CODE, UPDATE_EXIT_CODE, 0]

        def launch(command, stdin=None):
            started.append(FakeChildProcess(codes[len(started)]))
            return started[-1]

        swaps = [False, True]  # the first time nothing was ready: started again as it is
        launcher = ToolboxLauncher(["toolbox"], "http://127.0.0.1:8850", None, launch, ready=lambda url: True,
                                   update=lambda: swaps.pop(0))
        self.assertEqual((launcher.run(), len(started)), (0, 2))


if __name__ == "__main__":
    unittest.main()
