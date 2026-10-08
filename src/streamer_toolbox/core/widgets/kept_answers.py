import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

KEEP_SECONDS = 6 * 60 * 60


class KeptAnswers:
    """Answers kept for a while, so the same question isn't asked outside again: in memory and, with `path`, in
    that file (a restart keeps them). An answer is good for `keep_seconds`; at most `keep_count` are kept, the
    oldest go first. Answers must be plain data (they are written as JSON); None is an answer too ("not there")."""

    def __init__(self, path: Path | None = None, keep_count: int = 500, keep_seconds: float = KEEP_SECONDS,
                 clock: Callable[[], float] = time.time) -> None:
        self._path = path
        self._keep_count = keep_count
        self._keep_seconds = keep_seconds
        self._clock = clock
        self._kept: dict[str, tuple[float, Any]] = self._read()

    def __len__(self) -> int:
        return len(self._kept)

    def get(self, key: str) -> tuple[bool, Any]:
        """(whether a good answer is kept, the answer)."""
        kept = self._kept.get(key)
        if kept and self._clock() - kept[0] < self._keep_seconds:
            return True, kept[1]
        return False, None

    def keep(self, key: str, answer: Any) -> None:
        self._kept.pop(key, None)  # asked again: it's the newest now
        self._kept[key] = (self._clock(), answer)
        while len(self._kept) > self._keep_count:
            del self._kept[next(iter(self._kept))]
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({key: {"at": at, "answer": answer}
                                              for key, (at, answer) in self._kept.items()},
                                             ensure_ascii=False), encoding="utf-8")

    def _read(self) -> dict[str, tuple[float, Any]]:
        """What the file holds; a file that can't be read is no loss (the question is asked again)."""
        if self._path is None or not self._path.is_file():
            return {}
        try:
            saved = json.loads(self._path.read_text(encoding="utf-8"))
            return {str(key): (float(entry["at"]), entry["answer"]) for key, entry in saved.items()}
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return {}
