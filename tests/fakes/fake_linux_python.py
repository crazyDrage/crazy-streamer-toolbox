from pathlib import Path

from streamer_toolbox.devtools.package.linux_python import LinuxPython


class FakeLinuxPython(LinuxPython):
    """A LinuxPython that downloads and installs nothing: it puts a stand-in for the Python (and a cache
    folder a real one leaves behind) into the folder and remembers which requirements file it was given."""

    def __init__(self) -> None:
        super().__init__(Path("unused"), "3.14")
        self.requirements = ""

    def put(self, folder: Path, requirements: Path) -> str:
        self.requirements = requirements.name if requirements.is_file() else ""
        python = folder / "python" / "bin" / "python3"
        python.parent.mkdir(parents=True)
        python.write_text("the python", encoding="utf-8")
        cache = folder / "python" / "lib" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "x.pyc").write_text("compiled", encoding="utf-8")
        return "3.14.0"
