import tempfile
import zipfile
import unittest
from pathlib import Path

from streamer_toolbox.core.testing.release_marker import RELEASE_MARKER, is_release
from streamer_toolbox.devtools.package.packager import LINUX, WINDOWS, Packager
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

    def test_a_linux_build_carries_no_python(self) -> None:
        archive = ListedPackager(self.repo, self.out, target=LINUX).build()
        self.assertEqual(archive.name, "crazy-streamer-toolbox-linux.zip")
        with zipfile.ZipFile(archive) as packed:
            names = packed.namelist()
        self.assertIn("crazy-streamer-toolbox-linux/start-linux.sh", names)
        self.assertIn("crazy-streamer-toolbox-linux/requirements.txt", names)
        self.assertFalse([name for name in names if "/python/" in name or name.endswith(".bat")])

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
