import sys
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.system.program_actions import ProgramActions

PYTHON = sys.executable


class TestProgramActions(unittest.IsolatedAsyncioTestCase):
    async def test_runs_and_reads_what_it_printed(self) -> None:
        result = await ProgramActions().run(PYTHON, '-c "import json; print(json.dumps({\'clip\': \'a b.mp4\'}))"')
        self.assertEqual((result["output"], result["exit_code"]), ({"clip": "a b.mp4"}, 0))

    async def test_arguments_as_a_list_and_folder(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            result = await ProgramActions().run(PYTHON, ["-c", "import os; print(os.getcwd())"], folder=folder)
            self.assertEqual(Path(result["output"]).resolve(), Path(folder).resolve())

    async def test_failure_and_timeout(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exit code 3: boom"):
            await ProgramActions().run(PYTHON, '-c "import sys; sys.exit(\'boom\' and print(\'boom\', file=sys.stderr) '
                                               'or 3)"')
        result = await ProgramActions().run(PYTHON, '-c "raise SystemExit(2)"', fail_on_error="false")
        self.assertEqual(result["exit_code"], 2)
        with self.assertRaisesRegex(TimeoutError, "within 0.3 s"):
            await ProgramActions().run(PYTHON, '-c "import time; time.sleep(5)"', seconds=0.3)
        with self.assertRaisesRegex(FileNotFoundError, "can't start"):
            await ProgramActions().run("C:/no/such/program.exe")


if __name__ == "__main__":
    unittest.main()
