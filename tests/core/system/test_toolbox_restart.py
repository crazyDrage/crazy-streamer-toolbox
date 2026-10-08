import unittest

from streamer_toolbox.core.system.toolbox_restart import RESTART_EXIT_CODE, ToolboxRestart


class TestToolboxRestart(unittest.TestCase):
    def test_a_request_shuts_down_and_ends_with_the_restart_code(self) -> None:
        stopped = []
        restart = ToolboxRestart(lambda: stopped.append(True), available=True)
        self.assertEqual(restart.exit_code, 0)
        restart.request()
        self.assertEqual((stopped, restart.exit_code), ([True], RESTART_EXIT_CODE))

    def test_without_a_launcher_it_refuses(self) -> None:
        restart = ToolboxRestart(lambda: None, available=False)
        with self.assertRaises(RuntimeError):
            restart.request()
        self.assertEqual(restart.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
