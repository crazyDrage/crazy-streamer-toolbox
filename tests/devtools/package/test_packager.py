import tarfile
import tempfile
import zipfile
import unittest
from pathlib import Path

from streamer_toolbox.core.testing.release_marker import RELEASE_MARKER, is_release
from streamer_toolbox.devtools.package.packager import LINUX, WINDOWS, Packager
from tests.fakes.fake_linux_python import FakeLinuxPython
from tests.fakes.fake_python_packager import FakePythonPackager
from tests.fakes.fake_windows_launcher import FakeWindowsLauncher
from tests.fakes.listed_packager import TRACKED, ListedPackager


class TestPackager(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.repo = Path(self._dir.name) / "repo"
        self.out = Path(self._dir.name) / "out"
        for path in [*TRACKED, "config/toolbox.toml", "config/twitch_token.json", "memory/note.md",
                     "src/streamer_toolbox/untracked.py"]:
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text(path, encoding="utf-8")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_only_the_code_the_example_settings_and_the_user_docs_go_in(self) -> None:
        copied = ListedPackager(self.repo, self.out, tested_only=False)._files(self.out)
        files = sorted(p.relative_to(self.out).as_posix() for p in self.out.rglob("*") if p.is_file())
        self.assertEqual(files, ["README.md", "config/toolbox.example.toml", "docs/WIDGETS.md", "docs/ai/rules.md",
                                 "plugins/hello/main.py", "requirements.txt", "src/streamer_toolbox/__main__.py"])
        self.assertEqual(copied, len(files))
        self.assertEqual((self.out / "README.md").read_text(encoding="utf-8"), "docs/USER_GUIDE.md")  # the guide

    def test_a_build_carries_everything_unless_asked_for_tested_only(self) -> None:
        marker = self.out / "src" / "streamer_toolbox" / RELEASE_MARKER
        ListedPackager(self.repo, self.out)._files(self.out)
        self.assertFalse(is_release(marker.parent))
        ListedPackager(self.repo, self.out, tested_only=True)._files(self.out)
        self.assertTrue(is_release(marker.parent))
        self.assertFalse(is_release())  # the project folder itself never is

    def test_the_archive_gets_start_scripts_for_windows_and_linux(self) -> None:
        self.out.mkdir()
        Packager._start_scripts(self.out)
        windows = (self.out / "Start streamer-toolbox.bat").read_bytes()
        linux = (self.out / "start-linux.sh").read_bytes()
        self.assertIn(b"--open window %*\r\n", windows)
        self.assertTrue(linux.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r", linux)  # a Windows line end breaks a shell script
        self.assertIn(b'--open window "$@"', linux)
        self.assertIn(b"requirements.txt || {\n", linux)  # the doubled braces of the template became one
        self.assertIn(b'--open browser "$@"', (self.out / "start-linux-browser.sh").read_bytes())

    def test_a_build_for_one_system_gets_only_its_start_scripts(self) -> None:
        for target, scripts in ((WINDOWS, ["Start in the browser.bat", "Start streamer-toolbox.bat"]),
                                (LINUX, ["start-linux-browser.sh", "start-linux.sh"])):
            folder = self.out / target
            folder.mkdir(parents=True)
            Packager._start_scripts(folder, target)
            self.assertEqual(sorted(p.name for p in folder.iterdir()), scripts)

    def test_a_linux_build_carries_its_own_python_and_starts_with_it(self) -> None:
        python = FakeLinuxPython()
        archive = ListedPackager(self.repo, self.out, target=LINUX, linux_python=python).build()
        self.assertEqual(archive.name, "crazy-streamer-toolbox-linux.tar.gz")
        self.assertEqual(python.requirements, "requirements.txt")  # installed from the copied file
        root = "crazy-streamer-toolbox-linux/"
        with tarfile.open(archive) as packed:
            names = packed.getnames()
            script = packed.extractfile(root + "start-linux.sh").read()
            self.assertEqual(packed.getmember(root + "start-linux.sh").mode, 0o755)
        self.assertIn(root + "python/bin/python3", names)
        self.assertFalse([name for name in names if name.endswith(".bat") or "__pycache__" in name])
        self.assertIn(b'exec python/bin/python3 -m streamer_toolbox --open window "$@"', script)
        self.assertNotIn(b"venv", script)  # nothing is got or installed at the first start
        self.assertNotIn(b"\r", script)

    def test_the_start_program_is_built_where_a_windows_python_goes_in(self) -> None:
        with_exe, without = FakeWindowsLauncher(), FakeWindowsLauncher(compiler=False)
        packager = FakePythonPackager(self.repo, self.out, target=WINDOWS, launcher=with_exe)
        with zipfile.ZipFile(packager.build()) as packed:
            self.assertIn("crazy-streamer-toolbox-windows/crazy-streamer-toolbox.exe", packed.namelist())
            self.assertIn("crazy-streamer-toolbox-windows/Start streamer-toolbox.bat", packed.namelist())
        packager = FakePythonPackager(self.repo, self.out, target=WINDOWS, launcher=without)
        with zipfile.ZipFile(packager.build()) as packed:  # no compiler: the .bat files alone
            self.assertNotIn("crazy-streamer-toolbox-windows/crazy-streamer-toolbox.exe", packed.namelist())
        linux = FakeWindowsLauncher()
        ListedPackager(self.repo, self.out, target=LINUX, linux_python=FakeLinuxPython(), launcher=linux).build()
        self.assertEqual((with_exe.built, without.built, linux.built), (1, 0, 0))

    def test_a_shell_script_is_runnable_in_the_archive(self) -> None:
        self.out.mkdir()
        Packager._start_scripts(self.out)
        with zipfile.ZipFile(self.out / "a.zip", "w") as packed:
            Packager._pack(packed, self.out / "start-linux.sh", Path("x/start-linux.sh"))
            Packager._pack(packed, self.out / "Start in the browser.bat", Path("x/Start in the browser.bat"))
        with zipfile.ZipFile(self.out / "a.zip") as packed:
            self.assertEqual(packed.getinfo("x/start-linux.sh").external_attr >> 16, 0o100755)
            self.assertEqual(packed.read("x/start-linux.sh"), (self.out / "start-linux.sh").read_bytes())


if __name__ == "__main__":
    unittest.main()
