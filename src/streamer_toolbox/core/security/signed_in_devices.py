import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class SignedInDevices:
    """Which browsers signed in, by the id in their signed session cookie, with the password's session key at
    that time (a new password makes every entry stale). Kept in a JSON file so a restart doesn't sign them out."""

    def __init__(self, path: Path) -> None:
        self._path = path
        try:
            self._devices: dict[str, str] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except ValueError as e:
            log.error("%s unreadable, every device signs in again: %s", path.name, e)
            self._devices = {}

    def signed_in(self, browser_id: str | None, key: str) -> bool:
        return bool(browser_id) and bool(key) and self._devices.get(browser_id) == key

    def add(self, browser_id: str, key: str) -> None:
        self._devices = {b: k for b, k in self._devices.items() if k == key}  # drop ones from old passwords
        self._devices[browser_id] = key
        self._save()

    def remove(self, browser_id: str | None) -> None:
        if self._devices.pop(browser_id or "", None) is not None:
            self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._devices, indent=1), encoding="utf-8")
