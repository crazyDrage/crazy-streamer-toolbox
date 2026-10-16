from pathlib import Path

from streamer_toolbox.devtools.package.windows_launcher import EXE, WindowsLauncher


class FakeWindowsLauncher(WindowsLauncher):
    """A WindowsLauncher that compiles nothing: with a "compiler" it writes a stand-in for the start program
    and counts it, without one it says so like the real one."""

    def __init__(self, compiler: bool = True) -> None:
        self._has_compiler = compiler
        self.built = 0

    def compiler(self) -> str | None:
        return "gcc" if self._has_compiler else None

    def build(self, folder: Path) -> bool:
        if not self._has_compiler:
            return False
        (folder / EXE).write_text("the start program", encoding="utf-8")
        self.built += 1
        return True
