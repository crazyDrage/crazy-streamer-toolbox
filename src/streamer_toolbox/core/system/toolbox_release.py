from dataclasses import dataclass


@dataclass(frozen=True)
class ToolboxRelease:
    """A release of the toolbox on GitHub that is newer than this one: its version ("0.3.0"), what's new (the
    release's text), its page, and the download for this system with the SHA-256 GitHub lists for it."""

    version: str
    notes: str
    page: str
    asset: str
    url: str
    digest: str
