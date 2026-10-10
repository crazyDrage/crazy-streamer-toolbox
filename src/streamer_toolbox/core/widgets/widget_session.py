import json
import time
from pathlib import Path
from typing import Any

from streamer_toolbox.core.history.event_history import PERIODS, EventHistory

KINDS = ("follower", "subscriber", "cheer", "raid", "tip", "host")
GIVEN = ("cheer", "tip")  # kinds with an amount worth a "top giver"
RECENT = 25


class WidgetSession:
    """What happened since the toolbox started, in StreamElements' "session data" shape: per kind the latest one
    (`follower-latest`), how many / how much this session (`follower-session`, `cheer-session`), the recent ones
    (`follower-recent`) and `recents` over all kinds. Widgets read it when they load (onWidgetLoad) and get it
    again after each event (onSessionUpdate). Kinds the toolbox has no events for (tips, hosts) stay empty, so
    code that reads them finds the keys it expects.

    With a `path` the latest, the recent ones and the totals are kept in that file and are there again after a
    restart (a "latest follower" label isn't empty until the next follow); the `-session` counts start at 0.

    With a `history` (EventHistory) every event is also written into the toolbox's own dated record, and the
    keys StreamElements answers from its years of listening are answered from that record: `-week`, `-month`,
    `-total`, `-count`, and for cheers and tips `-session-` / `-weekly-` / `-monthly-` / `-alltime-top-donator`
    and `-top-donation`. refresh() works them out again (a new week or month starts by itself)."""

    def __init__(self, path: Path | None = None, history: EventHistory | None = None) -> None:
        self._path = path
        self._history = history
        self.recents: list[dict[str, Any]] = []
        self.data: dict[str, Any] = {}
        for kind in KINDS:
            self.data[f"{kind}-latest"] = {"name": "", "amount": 0, "message": ""}
            self.data[f"{kind}-session"] = {"count": 0, "amount": 0}
            self.data[f"{kind}-total"] = {"count": 0, "amount": 0}
            self.data[f"{kind}-recent"] = []
        self.data["subscriber-points"] = {"amount": 0}  # Twitch's sub points (SubscriberCount)
        self._load()
        self.refresh()

    def add(self, listener: str, event: dict[str, Any]) -> None:
        """One event that came in (a `...-latest` one; chat messages aren't session data)."""
        kind = listener.removesuffix("-latest")
        if kind == listener or kind not in KINDS:
            return
        entry = {**event, "type": kind, "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        self.data[listener] = entry
        amount = event.get("amount", 0) if isinstance(event.get("amount", 0), (int, float)) else 0
        for key in (f"{kind}-session", f"{kind}-total"):
            self.data[key] = {"count": self.data[key]["count"] + 1, "amount": self.data[key]["amount"] + amount}
        self.data[f"{kind}-recent"] = [entry, *self.data[f"{kind}-recent"]][:RECENT]
        self.recents = [entry, *self.recents][:RECENT]
        if self._history is not None:
            more = {key: event[key] for key in ("tier", "message", "gifted", "sender") if event.get(key)}
            self._history.record(kind, str(event.get("name") or ""), amount, **more)
            self.refresh()
        self._keep()

    def know(self, kind: str, entries: list[dict[str, Any]], total: Any = None) -> None:
        """What is known from elsewhere (Twitch's follower list): the newest ones of a kind, newest first, and
        how many there are in all. Replaces that kind's latest and recent ones; this session's count stays."""
        if kind not in KINDS:
            return
        if entries:
            self.data[f"{kind}-latest"] = entries[0]
            self.data[f"{kind}-recent"] = entries[:RECENT]
        if isinstance(total, int):
            self.data[f"{kind}-total"] = {"count": total, "amount": 0}
        self._keep()

    def refresh(self) -> None:
        """The sums over time, from the toolbox's own record. A count Twitch gave (followers, subscribers) stays
        when it is the bigger one: Twitch knows them all, the record only the ones it saw."""
        if self._history is None:
            return
        for kind in KINDS:
            sums = self._history.summary(kind)
            known = self.data[f"{kind}-total"]
            if sums["total"]["count"] >= known.get("count", 0) or kind in GIVEN:
                self.data[f"{kind}-total"] = dict(sums["total"])
            self.data[f"{kind}-count"] = {"count": self.data[f"{kind}-total"]["count"]}
            self.data[f"{kind}-week"] = dict(sums["week"])
            self.data[f"{kind}-month"] = dict(sums["month"])
            if kind in GIVEN:
                for period in PERIODS:
                    self.data[f"{kind}-{period}-top-donator"] = dict(sums["top"][period]["giver"])
                    self.data[f"{kind}-{period}-top-donation"] = dict(sums["top"][period]["biggest"])

    def points(self, amount: Any) -> None:
        """The channel's sub points, as Twitch counts them."""
        if isinstance(amount, int):
            self.data["subscriber-points"] = {"amount": amount}
            self._keep()

    def _load(self) -> None:
        try:
            kept = json.loads(self._path.read_text(encoding="utf-8")) if self._path and self._path.is_file() else {}
        except ValueError:
            return
        if not isinstance(kept, dict):
            return
        for key, start in list(self.data.items()):
            if not key.endswith("-session") and isinstance(kept.get("data", {}).get(key), type(start)):
                self.data[key] = kept["data"][key]
        if isinstance(kept.get("recents"), list):
            self.recents = kept["recents"][:RECENT]

    def _keep(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: value for key, value in self.data.items()
                if key.endswith(("-latest", "-recent", "-total", "-points"))}
        self._path.write_text(json.dumps({"data": data, "recents": self.recents}, ensure_ascii=False),
                              encoding="utf-8")
