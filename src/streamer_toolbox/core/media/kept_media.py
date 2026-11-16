from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Kept:
    """A file the media buffer keeps: `address` for overlays (on the toolbox's own address), `file` on this PC."""

    address: str
    file: Path
