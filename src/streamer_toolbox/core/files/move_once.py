import logging
from pathlib import Path

log = logging.getLogger(__name__)


def move_once(old: Path, new: Path) -> Path:
    """Where a file or folder is now that its place changed: moves `old` to `new` the first time (nothing is
    there yet) and gives `new`. If it can't be moved (open somewhere), `old` is given and keeps being used; the
    next start tries again."""
    if old.exists() and not new.exists():
        try:
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            log.info("moved %s to %s", old, new)
        except OSError as e:
            log.warning("%s stays where it is, it can't be moved to %s: %s", old, new, e)
            return old
    return new
