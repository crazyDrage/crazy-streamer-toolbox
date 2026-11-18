from dataclasses import dataclass


@dataclass(frozen=True)
class KeptFont:
    """A font the toolbox knows (Settings → Fonts): hosted (its files in the fonts folder, served to every
    device: `everywhere`) or by name only (a font of this PC, e.g. one that came with Windows: on this machine
    only)."""

    family: str
    everywhere: bool
    files: tuple[str, ...] = ()

    @property
    def mark(self) -> str:
        """His 11-18: every font is marked "all devices" or "on this machine only"."""
        return "All devices" if self.everywhere else "On this machine only"

    @property
    def icon(self) -> str:
        return "public" if self.everywhere else "computer"
