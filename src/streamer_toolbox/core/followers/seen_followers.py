import json
import logging
from collections.abc import Iterable
from pathlib import Path

from streamer_toolbox.core.files.write_whole import write_whole

log = logging.getLogger(__name__)
FOLLOWERS = "followers"  # the folder next to the settings: <platform>_<account>.json
KEEP = 5000  # the newest ones; an older follower that comes back after that counts as new


class SeenFollowers:
    """The followers one account of one platform has had, kept on disk (config/followers/<platform>_<account>.json),
    so the follower check and the platform's live event never thank the same follow twice, also after a restart
    (his failsafe of 2026-11-05: "check the last followers every minute and save them to a list locally").
    Without a path it only remembers while the toolbox runs (tests)."""

    def __init__(self, path: Path | None, keep: int = KEEP) -> None:
        self._path = path
        self._keep = keep
        self._filled, self._ids = self._load()
        self._known = set(self._ids)

    @property
    def empty(self) -> bool:
        """No check has filled it yet: the first one only fills the list (who followed before isn't news; a
        live follow seen before that doesn't count)."""
        return not self._filled

    def fill(self, followers: Iterable[str]) -> None:
        """The first check's followers: remembered, nothing sent."""
        self._filled = True
        self.remember(followers, save=True)

    def fresh(self, follower: str) -> bool:
        """True the first time a follower (their id) is seen; it is remembered from then on."""
        follower = str(follower).strip().casefold()
        if not follower or follower in self._known:
            return not follower  # no id: can't tell, so it is let through
        self.remember([follower])
        return True

    def remember(self, followers: Iterable[str], save: bool = False) -> None:
        new = [f for f in (str(f).strip().casefold() for f in followers) if f and f not in self._known]
        if not new and not save:
            return
        self._ids.extend(new)
        self._known.update(new)
        if len(self._ids) > self._keep:
            for old in self._ids[:-self._keep]:
                self._known.discard(old)
            self._ids = self._ids[-self._keep:]
        self._save()

    def _load(self) -> tuple[bool, list[str]]:
        if self._path is None or not self._path.is_file():
            return False, []
        try:
            found = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log.warning("%s not read (%s): the follower list starts again", self._path, e)
            return False, []
        ids = found.get("ids") if isinstance(found, dict) else None
        return (bool(found.get("filled")), [str(f) for f in ids]) if isinstance(ids, list) else (False, [])

    def _save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            write_whole(self._path, json.dumps({"filled": self._filled, "ids": self._ids}))
        except OSError as e:
            log.warning("%s not written (%s)", self._path, e)
