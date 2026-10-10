from pathlib import Path
from typing import Any


class FakeGithubProgram:
    """A GithubProgram that is always there: path() gives the file it was made with, update() the next of
    `versions` each time it is asked."""

    def __init__(self, file: Path, versions: tuple[str, ...] = ("1.0",)) -> None:
        self.file = file
        self.versions = list(versions)
        self.version = ""
        self.asked = 0

    async def path(self) -> Path:
        self.asked += 1
        return self.file

    async def update(self) -> dict[str, Any]:
        before, self.version = self.version, self.versions.pop(0) if self.versions else self.version
        return {"version": self.version, "updated": self.version != before}
