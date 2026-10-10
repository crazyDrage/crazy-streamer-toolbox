import json
from pathlib import Path
from typing import Any


class PointStore:
    """The viewers' points (the toolbox's own currency, like Mix It Up's): one number per viewer, kept in one
    file (config/points/points.json). A viewer is a name on a platform; names count without upper / lower case,
    so "VexFan" and "vexfan" on Twitch are one viewer, and the same name on YouTube is another. Points never go
    below 0. The name is shown the way it was written with capitals, when it ever was (chat's login is all small)."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._viewers: dict[str, dict[str, Any]] = {}  # "twitch:vexfan" → {"name", "platform", "points"}
        if path is not None and path.is_file():
            try:
                kept = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                kept = {}
            self._viewers = {key: value for key, value in (kept if isinstance(kept, dict) else {}).items()
                             if isinstance(value, dict) and isinstance(value.get("points"), int)}

    def get(self, viewer: str, platform: str = "twitch") -> int:
        return self._viewers.get(_key(viewer, platform), {}).get("points", 0)

    def add(self, viewer: str, amount: int, platform: str = "twitch") -> int:
        """Gives points (a minus number takes them, down to 0). The viewer's points after it."""
        return self.add_many([viewer], amount, platform)[0]

    def add_many(self, viewers: list[str], amount: int, platform: str = "twitch") -> list[int]:
        """The same amount for several viewers, written to the file once."""
        after = []
        for viewer in viewers:
            if not str(viewer).strip():
                raise ValueError("a viewer needs a name")
            entry = self._viewers.setdefault(_key(viewer, platform), {"points": 0})
            written = str(viewer).strip().lstrip("@")
            if not entry.get("name") or written != written.casefold():  # "VexFan" beats the login "vexfan"
                entry["name"] = written
            entry.update(platform=_platform(platform), points=max(0, entry["points"] + int(amount)))
            after.append(entry["points"])
        self._keep()
        return after

    def set(self, viewer: str, points: int, platform: str = "twitch") -> int:
        return self.add(viewer, int(points) - self.get(viewer, platform), platform)

    def spend(self, viewer: str, amount: int, platform: str = "twitch") -> bool:
        """Takes the amount if the viewer has that much; False (and nothing taken) if not."""
        if int(amount) < 0 or self.get(viewer, platform) < int(amount):
            return False
        self.add(viewer, -int(amount), platform)
        return True

    def top(self, count: int = 10) -> list[dict[str, Any]]:
        """The viewers with the most points: [{"user", "platform", "points"}], most first."""
        ranked = sorted(self._viewers.values(), key=lambda entry: (-entry["points"], entry.get("name", "").casefold()))
        return [{"user": entry.get("name", ""), "platform": entry.get("platform", ""), "points": entry["points"]}
                for entry in ranked[:max(0, int(count))]]

    def all(self) -> list[dict[str, Any]]:
        return self.top(len(self._viewers))

    def remove(self, viewer: str, platform: str = "twitch") -> None:
        if self._viewers.pop(_key(viewer, platform), None) is not None:
            self._keep()

    def _keep(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._viewers, ensure_ascii=False), encoding="utf-8")


def _platform(platform: str) -> str:
    return str(platform or "twitch").strip().casefold() or "twitch"


def _key(viewer: str, platform: str) -> str:
    return f"{_platform(platform)}:{str(viewer).strip().lstrip('@').casefold()}"
