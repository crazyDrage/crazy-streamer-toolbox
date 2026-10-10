import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
KEEP_DAYS = 40  # entries this young stay in memory (the week and month sums need them)
PERIODS = ("session", "weekly", "monthly", "alltime")


class EventHistory:
    """The toolbox's own record of what happened on the channel: every follow, sub, cheer, raid and tip with its
    date, one line each in a file that only grows (config/history/events.jsonl). From it the toolbox answers
    what StreamElements answers from its years of listening: how many and how much this session, this week,
    this month and in all, who gave most, the biggest single one, the recent ones. Nothing here asks anyone.

    What happened before the toolbox listened can be brought over once (carry): the count and amount so far and
    the top giver, per kind. Entries brought over with their date but already inside such a carried count are
    recorded with counted=False: they count for the week and the month, not twice for "in all".

    A week starts on Monday, a month on its 1st, both in the PC's time (Hex's reading of StreamElements'
    "-week" / "-month"). Reading the file once at start keeps only the sums and the last 40 days in memory."""

    def __init__(self, path: Path | None = None, clock: Callable[[], float] = time.time) -> None:
        self._path = path
        self._clock = clock
        self._started = clock()
        self._young: list[dict[str, Any]] = []
        self._all: dict[str, dict[str, Any]] = {}  # kind → {"count", "amount", "givers": {name: amount}, "biggest"}
        self._carried: set[str] = set()
        if path is not None and path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue  # a half-written last line after a crash
                if isinstance(entry, dict) and entry.get("kind"):
                    self._take(entry)

    def record(self, kind: str, name: str, amount: float = 0, at: float | None = None, counted: bool = True,
               **more: Any) -> None:
        """One thing that happened. at: unix time (now if not given). more: what else is worth keeping (tier,
        message, platform)."""
        entry = {"at": self._clock() if at is None else at, "kind": kind, "name": str(name or ""),
                 "amount": amount if isinstance(amount, (int, float)) and not isinstance(amount, bool) else 0,
                 **({} if counted else {"counted": False}), **more}
        self._take(entry)
        self._write(entry)

    def carry(self, kind: str, count: int = 0, amount: float = 0, top_giver: dict[str, Any] | None = None,
              biggest: dict[str, Any] | None = None) -> bool:
        """What was there before the toolbox listened, brought over once per kind. False if that kind already has
        a carried start (a second import must not add it again)."""
        if kind in self._carried:
            return False
        entry = {"at": self._clock(), "kind": kind, "carried": True, "count": int(count or 0), "amount": amount or 0,
                 "top_giver": _named(top_giver), "biggest": _named(biggest)}
        self._take(entry)
        self._write(entry)
        return True

    def carried(self, kind: str) -> bool:
        return kind in self._carried

    def known(self, kind: str) -> bool:
        """Whether anything of that kind was ever recorded or carried."""
        return kind in self._all

    def recent(self, kind: str, count: int = 25) -> list[dict[str, Any]]:
        """The newest ones of a kind from the last 40 days, newest first."""
        found = [entry for entry in self._young if entry["kind"] == kind]
        return sorted(found, key=lambda entry: entry["at"], reverse=True)[:count]

    def summary(self, kind: str) -> dict[str, Any]:
        """{"session" | "week" | "month" | "total": {"count", "amount"}, "top": {period: {"giver": {"name",
        "amount"}, "biggest": {"name", "amount"}}}} for session / weekly / monthly / alltime."""
        now = time.localtime(self._clock())
        midnight = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, 0, 0, -1))
        starts = {"session": self._started, "weekly": midnight - now.tm_wday * 86400,
                  "monthly": time.mktime((now.tm_year, now.tm_mon, 1, 0, 0, 0, 0, 0, -1))}
        whole = self._all.get(kind, {"count": 0, "amount": 0, "givers": {}, "biggest": _named(None)})
        sums = {"total": {"count": whole["count"], "amount": _tidy(whole["amount"])}}
        top = {"alltime": {"giver": _top(whole["givers"]), "biggest": dict(whole["biggest"])}}
        for period, start in starts.items():
            entries = [entry for entry in self._young if entry["kind"] == kind and entry["at"] >= start]
            givers: dict[str, float] = {}
            for entry in entries:
                if entry["name"]:
                    givers[entry["name"]] = givers.get(entry["name"], 0) + entry["amount"]
            biggest = max(entries, key=lambda entry: entry["amount"], default=None)
            key = {"weekly": "week", "monthly": "month"}.get(period, period)
            sums[key] = {"count": len(entries), "amount": _tidy(sum(entry["amount"] for entry in entries))}
            top[period] = {"giver": _top(givers), "biggest": _named(biggest if biggest and biggest["amount"] else None)}
        return {**sums, "top": top}

    def _take(self, entry: dict[str, Any]) -> None:
        whole = self._all.setdefault(entry["kind"], {"count": 0, "amount": 0, "givers": {}, "biggest": _named(None)})
        if entry.get("carried"):
            self._carried.add(entry["kind"])
            whole["count"] += entry.get("count", 0)
            whole["amount"] += entry.get("amount", 0)
            for key in ("top_giver", "biggest"):
                given = _named(entry.get(key))
                if key == "top_giver" and given["name"]:
                    whole["givers"][given["name"]] = whole["givers"].get(given["name"], 0) + given["amount"]
                if key == "biggest" and given["amount"] > whole["biggest"]["amount"]:
                    whole["biggest"] = given
            return
        entry.setdefault("name", "")
        entry["amount"] = entry.get("amount") if isinstance(entry.get("amount"), (int, float)) else 0
        entry["at"] = entry.get("at") if isinstance(entry.get("at"), (int, float)) else 0
        if entry.get("counted", True):
            whole["count"] += 1
            whole["amount"] += entry["amount"]
            if entry["name"]:
                whole["givers"][entry["name"]] = whole["givers"].get(entry["name"], 0) + entry["amount"]
            if entry["amount"] > whole["biggest"]["amount"]:
                whole["biggest"] = {"name": entry["name"], "amount": entry["amount"]}
        if entry["at"] >= self._clock() - KEEP_DAYS * 86400:
            self._young.append(entry)

    def _write(self, entry: dict[str, Any]) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:  # a full or locked disk must not stop the stream
            log.warning("history: the entry was not written (%s)", e)


def _named(given: Any) -> dict[str, Any]:
    if not isinstance(given, dict):
        return {"name": "", "amount": 0}
    amount = given.get("amount")
    return {"name": str(given.get("name") or ""), "amount": _tidy(amount) if isinstance(amount, (int, float)) else 0}


def _top(givers: dict[str, float]) -> dict[str, Any]:
    name = max(givers, key=givers.get, default="")
    return {"name": name, "amount": _tidy(givers.get(name, 0))}


def _tidy(amount: float) -> float | int:
    return int(amount) if amount == int(amount) else round(amount, 2)
