import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from streamer_toolbox.core.testing.release_marker import RELEASE_MARKER

PYTHON_ZIP = "https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"
# what goes into the archive from the repo: only files git knows, and only these. Never config/ (his settings
# and tokens), memory/, notes/, temp/, and not the docs written for the developers (HANDOFF, HISTORY, plans)
SHARED = ("src/", "plugins/", "config/toolbox.example.toml", "requirements.txt", "llms.txt", "docs/ai/",
          "docs/tested/", "LICENSE", "NOTICE")  # docs/tested/: what was tested; Settings → What you see shows by it
DOCS = {"docs/USER_GUIDE.md": "README.md", "docs/WIDGETS.md": "docs/WIDGETS.md",
        "docs/PLUGINS.md": "docs/PLUGINS.md"}
START = """@echo off
rem Starts streamer-toolbox and opens it in its own window. Closing that window stops it.
rem Everything it needs is in this folder; nothing is installed on the PC.
cd /d "%~dp0"
"python\\python.exe" -m streamer_toolbox --open {open} %*
if errorlevel 1 pause
"""
# Linux has no Python to carry along like Windows' embeddable package: the script makes a .venv in the folder
# on the first start, with the PC's own python3, and installs the libraries into it. 3.12 or newer: on 3.11
# asyncio.wait_for can swallow a cancel, and a connection's stop then never returns. The keyboard library
# (pynput) brings evdev, which pip has to compile: that is what gcc and python3-dev are for
LINUX_START = """#!/bin/sh
# Starts streamer-toolbox on Linux and opens it {how}.
# The first start needs python3 (3.12 or newer, with venv), a C compiler and the internet: it puts the
# libraries into a .venv folder here. Nothing is installed outside this folder.
cd "$(dirname "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
    python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || {{
        echo "streamer-toolbox needs python3 version 3.12 or newer. This PC has: $(python3 --version 2>&1)"
        exit 1
    }}
    echo "First start: getting the libraries (a minute or two) ..."
    python3 -m venv .venv && .venv/bin/python -m pip install --quiet -r requirements.txt || {{
        echo "That did not work. It needs python3 with venv and a C compiler, e.g."
        echo "    sudo apt install python3-venv python3-dev gcc"
        rm -rf .venv
        exit 1
    }}
fi
PYTHONPATH="$(pwd)/src" exec .venv/bin/python -m streamer_toolbox --open {open} "$@"
"""
SCRIPTS = (("Start streamer-toolbox.bat", START, "window", "ascii", "\r\n"),
           ("Start in the browser.bat", START, "browser", "ascii", "\r\n"),
           ("start-linux.sh", LINUX_START, "window", "utf-8", "\n"),
           ("start-linux-browser.sh", LINUX_START, "browser", "utf-8", "\n"))
WINDOWS, LINUX = "windows", "linux"  # a build for one of them only; "" = the one archive that starts on both
HOW = {"window": "in its own window (a browser tab without a Chromium browser)", "browser": "as a browser tab"}


class Packager:
    """Builds the archive to send people: a folder with the toolbox, its own Python (python.org's "embeddable
    package", the version this runs on) and every library from requirements.txt, plus the user guide and a
    start script to double-click. Nothing has to be installed on the other PC. Windows, 64 bit.
    The same archive starts on Linux with start-linux.sh, which uses that PC's python3 (see LINUX_START).

    Only files git tracks are copied, and of those only the code, the plugins, the example settings and the
    user docs: his own config/ (settings, tokens, flows, widgets) can't get in. build() gives the zip's path;
    the downloaded Python is kept in <build>/cache for the next time.

    A build carries everything, with the test record (docs/tested/, see TestList): what of it people see they
    choose themselves in Settings → What you see, which starts on "Tested" (TestView). tested_only=True builds
    one that leaves out what is not ticked off there: it gets the marker file that tells the toolbox so.

    target = WINDOWS or LINUX builds a download for that system only (the releases, built by GitHub):
    crazy-streamer-toolbox-windows.zip has the Python and the .bat scripts, crazy-streamer-toolbox-linux.zip
    neither (start-linux.sh gets the libraries on the first start). The Windows one can be built on Linux:
    the libraries are then taken as ready-made Windows packages."""

    def __init__(self, repo: Path, build: Path, version: str = "", tested_only: bool = False,
                 target: str = "") -> None:
        self._repo = repo
        self._build = build
        self._tested_only = tested_only
        self._target = target
        self._version = version or "{}.{}.{}".format(*sys.version_info[:3])

    def build(self, name: str = "") -> Path:
        name = name or (f"crazy-streamer-toolbox-{self._target}" if self._target else "streamer-toolbox")
        folder = self._build / name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        if self._target != LINUX:
            self._python(folder / "python")
            self._libraries(folder / "python" / "Lib" / "site-packages")
        copied = self._files(folder)
        self._start_scripts(folder, self._target)
        archive = self._build / f"{name}.zip"
        archive.unlink(missing_ok=True)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for file in sorted(folder.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    self._pack(packed, file, Path(name) / file.relative_to(folder))
        # no arrow in it: not every console can print one
        print(f"{'only what is tested' if self._tested_only else 'everything in it (Settings, What you see)'}: "
              f"{copied} toolbox files, {'no Python' if self._target == LINUX else f'Python {self._version}'} "
              f"-> {archive} "
              f"({archive.stat().st_size / 1e6:.1f} MB)")
        return archive

    @staticmethod
    def _start_scripts(folder: Path, target: str = "") -> None:
        for script, text, how, encoding, line_end in SCRIPTS:
            if target and (target == LINUX) != script.endswith(".sh"):
                continue  # the other system's script
            (folder / script).write_text(text.format(open=how, how=HOW[how]), encoding=encoding, newline=line_end)

    @staticmethod
    def _pack(packed: zipfile.ZipFile, file: Path, name: Path) -> None:
        """Adds one file; a shell script is marked as runnable, so Linux starts it after unpacking."""
        if file.suffix != ".sh":
            packed.write(file, name)
            return
        info = zipfile.ZipInfo.from_file(file, name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100755 << 16
        packed.writestr(info, file.read_bytes())

    def tracked(self) -> list[str]:
        """The files git tracks, as paths from the repo's root."""
        listed = subprocess.run(["git", "ls-files"], cwd=self._repo, capture_output=True, text=True, check=True)
        return [line for line in listed.stdout.splitlines() if line]

    def _python(self, folder: Path) -> None:
        cache = self._build / "cache" / f"python-{self._version}-embed-amd64.zip"
        if not cache.is_file():
            cache.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(PYTHON_ZIP.format(version=self._version), cache)
        with zipfile.ZipFile(cache) as packed:
            packed.extractall(folder)
        # an embedded Python only looks where its ._pth file says: add the toolbox's code and the libraries
        pth = next(folder.glob("python*._pth"))
        zipped = next(line for line in pth.read_text(encoding="ascii").splitlines() if line.endswith(".zip"))
        pth.write_text("\n".join((zipped, ".", "Lib\\site-packages", "..\\src", "import site")) + "\n",
                       encoding="ascii")

    def _libraries(self, folder: Path) -> None:
        folder.mkdir(parents=True)
        # built on another system than Windows: take the ready-made Windows packages, never compile for this one
        cross = [] if sys.platform == "win32" else [
            "--platform", "win_amd64", "--implementation", "cp", "--only-binary=:all:",
            "--python-version", ".".join(self._version.split(".")[:2])]
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-compile", "--target", str(folder),
                        *cross, "-r", str(self._repo / "requirements.txt")], check=True)

    def _files(self, folder: Path) -> int:
        tracked = self.tracked()
        wanted = {path: path for path in tracked if path.startswith(SHARED) or path in SHARED}
        wanted.update({path: target for path, target in DOCS.items() if path in tracked})
        for path, target in wanted.items():
            (folder / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self._repo / path, folder / target)
        if self._tested_only:
            marker = folder / "src" / "streamer_toolbox" / RELEASE_MARKER
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("This build only offers what was tested. Delete this file to see everything.\n",
                              encoding="utf-8")
        return len(wanted)
