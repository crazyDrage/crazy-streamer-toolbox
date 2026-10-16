from pathlib import Path

from tests.fakes.listed_packager import ListedPackager


class FakePythonPackager(ListedPackager):
    """A ListedPackager that downloads no Windows Python and installs no libraries: it only makes their
    folders, so a whole Windows build can be gone through in a test."""

    def _python(self, folder: Path) -> None:
        folder.mkdir(parents=True)
        (folder / "python.exe").write_text("the python", encoding="utf-8")

    def _libraries(self, folder: Path) -> None:
        folder.mkdir(parents=True)
