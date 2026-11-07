from dataclasses import dataclass

from streamer_toolbox.core.exports.export_part import KINDS

NEW, SAME, TAKEN = "new", "same", "taken"
REPLACE, BOTH, SKIP = "replace", "both", "skip"
CHOICES = {REPLACE: "Replace yours", BOTH: "Keep both (new name)", SKIP: "Skip (keep yours)"}


@dataclass(frozen=True)
class ImportRow:
    """One part of an export in the import window: new here, the same as here (nothing to do), or taken (a part
    of that name is here and differs: he picks Replace, Keep both or Skip; `choice` is the one picked first)."""

    kind: str
    key: str
    title: str
    state: str
    choice: str = ""
    choices: tuple[str, ...] = ()

    @property
    def id(self) -> tuple[str, str]:
        return self.kind, self.key

    @property
    def label(self) -> str:
        return f"{KINDS.get(self.kind, self.kind)}: {self.title}"

    @property
    def said(self) -> str:
        return {NEW: "new", SAME: "the same as yours, nothing to do", TAKEN: "you have one with this name"}[self.state]
