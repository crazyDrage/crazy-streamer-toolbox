import logging
import os
import time
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

TRIES = 10
WAIT = 0.05  # seconds between tries


def write_whole(path: Path, data: str | bytes, encoding: str = "utf-8") -> None:
    """Writes the whole file or nothing: first into `<name>.<code>.tmp` next to it, then swapped in. A crash, or a
    backup reading the settings folder at that moment, sees the old file or the new one, never half of one
    (vtuber-backup's wish, 2026-11-03).

    On Windows the swap fails while another program holds the file open (a backup zipping it). It tries again
    for half a second; after that it writes straight into the file as before, so nothing is lost.

    Each write has its own .tmp (the <code>): two threads writing the same file at once each swap in their own,
    the last one wins. With one shared .tmp the first swap took the other's away and that one failed (his
    11-18: emotes in a kept chat list missing for the first loads, MediaBuffer's index written by ~40 picture
    requests at once)."""
    path = Path(path)
    raw = data.encode(encoding) if isinstance(data, str) else bytes(data)
    half = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    half.write_bytes(raw)
    for attempt in range(TRIES):
        try:
            os.replace(half, path)
            return
        except PermissionError:
            if attempt + 1 < TRIES:
                time.sleep(WAIT)
    log.warning("%s is held open by another program, written straight into it", path)
    half.unlink(missing_ok=True)
    path.write_bytes(raw)
