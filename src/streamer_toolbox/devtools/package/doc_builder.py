import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

MANUAL = "docs/manual"  # the Sphinx source: three parts (user, plugin creator, tool developer)
# what an AI agent reads: llms.txt (the index) and the files it leads to, at the same paths as in the repo
FOR_AI = ("llms.txt", "LICENSE", "NOTICE", "docs/USER_GUIDE.md", "docs/WIDGETS.md", "docs/PLUGINS.md")
FOR_AI_FOLDER = "docs/ai"


class DocBuilder:
    """Builds the docs as their own download, apart from the toolbox's archive: a folder with `manual/` (the
    Sphinx manual as web pages, open manual/index.html) and `for-ai/` (llms.txt and the Markdown files it
    leads to), zipped. Needs requirements-docs.txt installed. A warning from Sphinx fails the build, so a
    page that points at a heading or file that is gone is noticed here."""

    def __init__(self, repo: Path, build: Path) -> None:
        self._repo = repo
        self._build = build

    def build(self, name: str = "streamer-toolbox-docs") -> Path:
        folder = self._build / name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        self._manual(folder / "manual")
        copied = self._for_ai(folder / "for-ai")
        archive = self._build / f"{name}.zip"
        archive.unlink(missing_ok=True)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for file in sorted(folder.rglob("*")):
                if file.is_file():
                    packed.write(file, Path(name) / file.relative_to(folder))
        print(f"the manual and {copied} files for AI agents -> {archive} ({archive.stat().st_size / 1e6:.1f} MB)")
        return archive

    def for_ai_files(self) -> list[str]:
        """The files of the for-ai folder, as paths from the repo's root."""
        folder = self._repo / FOR_AI_FOLDER
        found = sorted(file.relative_to(self._repo).as_posix() for file in folder.rglob("*.md"))
        return [path for path in FOR_AI if (self._repo / path).is_file()] + found

    def _manual(self, folder: Path) -> None:
        subprocess.run([sys.executable, "-m", "sphinx", "-b", "html", "-q", "-W", "--keep-going", "-E",
                        "-d", str(self._build / "cache" / "doctrees"), str(self._repo / MANUAL), str(folder)],
                       check=True)
        shutil.rmtree(folder / ".doctrees", ignore_errors=True)
        (folder / ".buildinfo").unlink(missing_ok=True)

    def _for_ai(self, folder: Path) -> int:
        files = self.for_ai_files()
        for path in files:
            (folder / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self._repo / path, folder / path)
        return len(files)
