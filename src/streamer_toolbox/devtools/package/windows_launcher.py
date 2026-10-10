import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).with_suffix(".c")
EXE = "crazy-streamer-toolbox.exe"
# a gcc that makes Windows programs: MinGW's; on Windows it is also just called "gcc"
COMPILERS = ("x86_64-w64-mingw32-gcc",) + (("gcc",) if sys.platform == "win32" else ())


class WindowsLauncher:
    """The Windows download's start program (windows_launcher.c): a small .exe to double-click, which starts
    the Python next to it without a console window. People trust a program more than a .bat file; Windows'
    "protected your PC" warning is the same for both until the program is signed.

    Needs a gcc that makes Windows programs (MinGW; GitHub's Windows runner has one). build() gives False
    when there is none, and the download then only has the .bat files."""

    def compiler(self) -> str | None:
        return next((found for found in map(shutil.which, COMPILERS) if found), None)

    def build(self, folder: Path) -> bool:
        """Compiles the start program into `folder`; False if this PC has no compiler for it."""
        compiler = self.compiler()
        if compiler is None:
            return False
        subprocess.run([compiler, "-O2", "-s", "-municode", "-mwindows", str(SOURCE), "-o", str(folder / EXE)],
                       check=True)
        return True
