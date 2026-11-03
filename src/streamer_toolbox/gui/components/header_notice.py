from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class HeaderNotice:
    """A short notice next to the toolbox's name in the header, on every page (his answer of 2026-11-01:
    "next to the toolbox name"); a press shows `about`, the whole story, or does `on_press` (the update opens
    its own window). Settings from a newer toolbox, a new version, an update that failed."""

    text: str
    about: str
    icon: str = "warning"
    on_press: Callable[[], None] | None = None
    color: str = "warning"  # a Quasar colour: warning (yellow) for what went wrong, primary for good news
