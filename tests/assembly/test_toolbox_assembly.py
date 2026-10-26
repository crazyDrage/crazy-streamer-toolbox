import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class TestToolboxAssembly(unittest.TestCase):
    """The whole start (assemble()) on the default settings, in its own process: every part is built and
    every box is added without an error. Nothing connects and no port is opened."""

    def test_a_start_on_the_defaults_adds_the_boxes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO / "src"), str(REPO)])}
            done = subprocess.run([sys.executable, "-m", "tests.helpers.assemble_once", folder], cwd=folder,
                                  env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(done.returncode, 0, done.stderr[-3000:])
            written = {p.relative_to(folder).parts[0] for p in Path(folder).iterdir()}
        names = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertGreater(len(names), 200)
        self.assertEqual(written, {"config", "plugins"})  # nothing beside its own folders
        some = {"logic.if", "logic.wait_for_all", "obs.switch_scene", "twitch.send_chat", "sound.stop_all",
                "text.replace", "points.add", "alert.show"}
        self.assertEqual(some - set(names), set())


if __name__ == "__main__":
    unittest.main()
