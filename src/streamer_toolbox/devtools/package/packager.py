import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from collections.abc import Mapping
from pathlib import Path

from streamer_toolbox.core.app_version import APP_VERSION
from streamer_toolbox.devtools.package.linux_python import LinuxPython
from streamer_toolbox.devtools.package.windows_launcher import EXE, WindowsLauncher

PYTHON_ZIP = "https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"
# what goes into the archive from the repo: only files git knows, and only these. Never config/ (his settings
# and tokens), memory/, notes/, temp/, and not the docs written for the developers (HANDOFF, HISTORY, plans)
SHARED = ("src/", "plugins/", "config/toolbox.example.toml", "requirements.txt", "llms.txt", "docs/ai/",
          "docs/tested/", "LICENSE", "NOTICE")  # docs/tested/: what was tested; Settings → What you see shows by it
DOCS = {"docs/USER_GUIDE.md": "README.md", "docs/WIDGETS.md": "docs/WIDGETS.md",
        "docs/PLUGINS.md": "docs/PLUGINS.md"}
START = """@echo off
rem Starts streamer-toolbox and {how}. Closing this console stops it too.
rem Everything it needs is in this folder; nothing is installed on the PC.
cd /d "%~dp0"
"python\\python.exe" -m {run} %*
if errorlevel 1 pause
"""
# The archive for both systems carries no Python for Linux: the script makes a .venv in the folder
# on the first start, with the PC's own python3, and installs the libraries into it. 3.12 or newer: on 3.11
# asyncio.wait_for can swallow a cancel, and a connection's stop then never returns. The keyboard library
# (pynput) brings evdev, which pip has to compile: that is what gcc and python3-dev are for
LINUX_START = """#!/bin/sh
# streamer-toolbox on Linux: {how}.
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
PYTHONPATH="$(pwd)/src" exec .venv/bin/python -m {run} "$@"
"""
# the Linux download brings its Python and the libraries (LinuxPython): nothing to get, nothing to install
LINUX_OWN_START = """#!/bin/sh
# streamer-toolbox on Linux: {how}.
# Everything it needs is in this folder; nothing is installed on the PC.
cd "$(dirname "$0")" || exit 1
PYTHONPATH="$(pwd)/src" exec python/bin/python3 -m {run} "$@"
"""
# start-settings (his round 84): the starter window, without a console (pythonw), so this closes at once
SETTINGS_START = """@echo off
rem Opens the small streamer-toolbox window: {how}.
rem Everything it needs is in this folder; nothing is installed on the PC.
cd /d "%~dp0"
start "" "python\\pythonw.exe" -m {run} %*
"""
WINDOW, HEADLESS, SETTINGS = ("streamer_toolbox --open window", "streamer_toolbox --open none",
                              "streamer_toolbox.starter")
# his 2026-11-03: three ways to start, the same on both systems; browser tab and less memory are in start-settings
SCRIPTS = (("Start streamer-toolbox.bat", START, WINDOW, "ascii", "\r\n"),
           ("Start without a window.bat", START, HEADLESS, "ascii", "\r\n"),
           ("Start settings.bat", SETTINGS_START, SETTINGS, "ascii", "\r\n"),
           ("start-linux.sh", LINUX_START, WINDOW, "utf-8", "\n"),
           ("start-linux-headless.sh", LINUX_START, HEADLESS, "utf-8", "\n"),
           ("start-linux-settings.sh", LINUX_START, SETTINGS, "utf-8", "\n"))
WINDOWS, LINUX = "windows", "linux"  # a build for one of them only; "" = the one archive that starts on both
HOW = {WINDOW: "opens it in its own window (a browser tab without a Chromium browser); closing it stops it",
       HEADLESS: "runs it without a window: open http://127.0.0.1:8850 in any browser or on your phone",
       SETTINGS: "pick how the toolbox opens, start it, back up its settings (a tray icon next to the clock)"}


class Packager:
    """Builds the archive to send people: a folder with the toolbox, its own Python (python.org's "embeddable
    package", the version this runs on) and every library from requirements.txt, plus the user guide and a
    start script to double-click. Nothing has to be installed on the other PC. Windows, 64 bit.
    The same archive starts on Linux with start-linux.sh, which uses that PC's python3 (see LINUX_START).

    Only files git tracks are copied, and of those only the code, the plugins, the example settings and the
    user docs: his own config/ (settings, tokens, flows, widgets) can't get in. build() gives the zip's path;
    the downloaded Python is kept in <build>/cache for the next time.

    A build carries everything, with the test record (docs/tested/, see TestList): what of it people see they
    choose themselves in Settings → What you see, which starts on Normal with Works ticked (TestView).

    target = WINDOWS or LINUX builds a download for that system only (the releases, built by GitHub), each
    with its own Python, so nothing is installed on the other PC: crazy-streamer-toolbox-windows.zip (the .bat
    scripts) and crazy-streamer-toolbox-linux.tar.gz (the .sh scripts; a tar keeps what Linux needs: which
    files may run, and links). The Windows one can be built on Linux: the libraries are then taken as
    ready-made Windows packages. The Linux one only on Linux (see LinuxPython).

    With a Windows Python the archive also gets crazy-streamer-toolbox.exe, a start program to double-click
    (WindowsLauncher), if the PC that builds has a compiler for it; without one it has only the .bat files."""

    def __init__(self, repo: Path, build: Path, version: str = "",
                 target: str = "", linux_python: LinuxPython | None = None,
                 launcher: WindowsLauncher | None = None) -> None:
        self._repo = repo
        self._build = build
        self._target = target
        self._version = version or "{}.{}.{}".format(*sys.version_info[:3])
        self._linux_python = linux_python or LinuxPython(build / "cache", ".".join(self._version.split(".")[:2]))
        self._launcher = launcher or WindowsLauncher()

    def build(self, name: str = "") -> Path:
        name = name or (f"crazy-streamer-toolbox-{self._target}" if self._target else "streamer-toolbox")
        folder = self._build / name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        python = self._version
        copied = self._files(folder)  # before the Linux Python: it installs from the copied requirements.txt
        if self._target == LINUX:
            python = self._linux_python.put(folder, folder / "requirements.txt")
        else:
            self._python(folder / "python")
            self._tkinter(folder / "python")
            self._libraries(folder / "python" / "Lib" / "site-packages")
            if not self._launcher.build(folder):
                print(f"no {EXE} in this build (this PC has no gcc for Windows programs): only the .bat files")
        self._start_scripts(folder, self._target)
        archive = self._tar(folder, name) if self._target == LINUX else self._zip(folder, name)
        # no arrow in it: not every console can print one
        print(f"everything in it (Settings, What you see): {copied} toolbox files, Python {python} -> {archive} ({archive.stat().st_size / 1e6:.1f} MB)")
        return archive

    def _zip(self, folder: Path, name: str) -> Path:
        archive = self._build / f"{name}.zip"
        archive.unlink(missing_ok=True)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for file in sorted(folder.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    self._pack(packed, file, Path(name) / file.relative_to(folder))
        return archive

    def _tar(self, folder: Path, name: str) -> Path:
        """The Linux download: links stay links, and what may run stays runnable (the start scripts always)."""
        def entry(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
            if "__pycache__" in info.name.split("/"):
                return None
            if info.name.endswith(".sh"):
                info.mode = 0o755
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            return info

        archive = self._build / f"{name}.tar.gz"
        archive.unlink(missing_ok=True)
        with tarfile.open(archive, "w:gz") as packed:
            packed.add(folder, arcname=name, filter=entry)
        return archive

    @staticmethod
    def _start_scripts(folder: Path, target: str = "") -> None:
        for script, text, run, encoding, line_end in SCRIPTS:
            if target and (target == LINUX) != script.endswith(".sh"):
                continue  # the other system's script
            if target == LINUX:
                text = LINUX_OWN_START
            (folder / script).write_text(text.format(run=run, how=HOW[run]), encoding=encoding, newline=line_end)

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

    def _tkinter(self, folder: Path, base: Path | None = None) -> bool:
        """The embeddable Python has no tkinter, which start-settings (the starter window) needs: _tkinter and the
        Tcl/Tk DLLs (zlib1 is theirs), the tkinter package and Tcl/Tk's own files, from this PC's own Windows
        Python of the same version (on GitHub: setup-python's). ~8 MB. False (and says so) when there is none."""
        base = base or Path(sys.base_prefix)
        folder_dlls = base / "DLLs"
        # whatever Tcl/Tk this Python has, wherever it keeps them: DLLs/ here, elsewhere in GitHub's setup-python
        # (3.14.10 had none in DLLs/); tcl86t.dll / tk86t.dll, or tcl90.dll / tcl9tk90.dll with Tcl/Tk 9
        found = {p.name.casefold(): p for p in sorted(base.rglob("*.dll"))
                 if "site-packages" not in p.parts and p.name.casefold().startswith(("tcl", "tk", "zlib"))}
        dlls = [folder_dlls / "_tkinter.pyd", *found.values()]
        missing = [what for what, there in (
            ("a Windows Python", sys.platform == "win32"),
            ("the same Python version", "{}.{}".format(*sys.version_info[:2]) == ".".join(self._version.split(".")[:2])),
            (f"{folder_dlls / '_tkinter.pyd'}", dlls[0].is_file()),
            (f"Tcl and Tk DLLs anywhere in {base}", any(p.name.casefold().startswith("tk") for p in dlls[1:])),
            (f"{base / 'Lib' / 'tkinter'}", (base / "Lib" / "tkinter").is_dir()),
            (f"{base / 'tcl'}", (base / "tcl").is_dir())) if not there]
        if missing:
            there = sorted(p.name for p in folder_dlls.glob("*")) if folder_dlls.is_dir() else []
            print("no tkinter in this build, start-settings won't open. Missing: " + "; ".join(missing)
                  + f". In {folder_dlls}: " + ", ".join(there))
            return False
        print("tkinter from " + str(base) + ": " + ", ".join(p.name for p in dlls))
        for dll in dlls:
            shutil.copyfile(dll, folder / dll.name)
        ignore = shutil.ignore_patterns("__pycache__", "*.lib", "test", "tests")
        shutil.copytree(base / "Lib" / "tkinter", folder / "tkinter", ignore=ignore)
        shutil.copytree(base / "tcl", folder / "tcl", ignore=ignore)
        return True

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
        return len(wanted)


def tag_problem(env: Mapping[str, str]) -> str:
    """A release build (GitHub, for a version tag) whose tag isn't this code's APP_VERSION: what is wrong, else
    "". Without it a release could carry an old version number, and every toolbox would offer it as new
    forever (ToolboxUpdate compares against APP_VERSION)."""
    if env.get("GITHUB_REF_TYPE") != "tag":
        return ""
    tag = env.get("GITHUB_REF_NAME", "")
    if tag != f"v{APP_VERSION}":
        return f"the tag is {tag}, but core/app_version.py says {APP_VERSION}: raise APP_VERSION in the release commit"
    return ""
