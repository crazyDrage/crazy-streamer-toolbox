import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.files.write_whole import write_whole

log = logging.getLogger(__name__)

MONTH = 30 * 24 * 60 * 60  # a value kept without a max age goes after this (his round 90: "default 1 months?")
USED_EVERY = 60  # "last used" counts in the file at most once a minute per value (it is written with the next set)


class RememberedValues:
    """Values a flow keeps for a while under a name, so it doesn't ask outside again (his round 90: "if we have the
    same person send a chat message every few seconds, we don't need to request the pfp link every time"). Kept
    in memory and in `path` (a restart keeps them), apart from the variables.

    Values are kept in groups (a box's Group, e.g. "twitch_pfp"), each with its own most count: when a group is
    fuller, the values unused the longest go. Every value has the max age it was kept with: older, it isn't
    found, and it goes the next time its group is written (or at start). There is no "forever" (his round 90:
    "that will result in a never ending growing cache"): no max age = a month.

    Values must be plain data (they are written as JSON); anything else is kept as its text."""

    def __init__(self, path: Path | None = None, clock: Callable[[], float] = time.time) -> None:
        self._path = path
        self._clock = clock
        self._groups: dict[str, dict[str, dict[str, Any]]] = self._read()

    def get(self, group: str, key: str, max_age: float) -> tuple[bool, Any, float]:
        """(whether a value younger than max_age seconds is kept, the value, its age in seconds)."""
        kept = self._groups.get(group, {}).get(key)
        if kept is None:
            return False, None, 0.0
        now = self._clock()
        age = max(0.0, now - kept["at"])
        if age > _seconds(max_age) or age > kept["keep"]:
            return False, None, age
        if now - kept["used"] >= USED_EVERY:
            kept["used"] = now
        return True, kept["value"], age

    def set(self, group: str, key: str, value: Any, max_age: float, most: int) -> None:
        """Keeps value under key for max_age seconds (0 = a month); the group keeps at most `most` values."""
        now = self._clock()
        values = self._groups.setdefault(group, {})
        values.pop(key, None)
        values[key] = {"value": _plain(value), "at": now, "used": now, "keep": _seconds(max_age)}
        for gone in [k for k, v in values.items() if now - v["at"] > v["keep"]]:
            del values[gone]
        extra = len(values) - max(1, int(most))
        if extra > 0:
            for gone in sorted(values, key=lambda k: values[k]["used"])[:extra]:
                del values[gone]
        self._save()

    def forget(self, flow: str, boxes: list[str]) -> None:
        """Boxes left out of a flow at Save flow (FlowLibrary.boxes_gone): their own groups go."""
        gone = [own_group(flow, box) for box in boxes if own_group(flow, box) in self._groups]
        for group in gone:
            del self._groups[group]
        if gone:
            self._save()

    def count(self, group: str) -> int:
        return len(self._groups.get(group, {}))

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(self._path, json.dumps(self._groups, ensure_ascii=False))

    def _read(self) -> dict[str, dict[str, dict[str, Any]]]:
        """What the file holds, without what is too old; a file that can't be read is no loss (asked again)."""
        if self._path is None or not self._path.is_file():
            return {}
        try:
            saved = json.loads(self._path.read_text(encoding="utf-8"))
            now = self._clock()
            groups = {}
            for group, values in saved.items():
                kept = {str(key): {"value": entry["value"], "at": float(entry["at"]),
                                   "used": float(entry.get("used", entry["at"])), "keep": float(entry["keep"])}
                        for key, entry in values.items()}
                groups[str(group)] = {k: v for k, v in kept.items() if now - v["at"] <= v["keep"]}
            return groups
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
            log.warning("remembered values not read (%s): they are asked again", e)
            return {}


def own_group(flow: str, box: str) -> str:
    """The group of a box with an empty Group field: its own, by flow and box id."""
    return f"box:{flow}/{box}"


def _seconds(max_age: float) -> float:
    seconds = float(max_age or 0)
    return seconds if seconds > 0 else MONTH


def _plain(value: Any) -> Any:
    """The value as JSON keeps it: plain data stays, anything else becomes its text."""
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError):
        return str(value)
