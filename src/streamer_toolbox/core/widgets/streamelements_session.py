from datetime import datetime
from typing import Any

import httpx

from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.widget_session import KINDS, WidgetSession

API = "https://api.streamelements.com/kappa/v2/sessions"


class StreamElementsSession:
    """Brings over what StreamElements knows as the latest subscriber, cheer, raid, tip (its "session data"),
    once, when he asks for it. The toolbox only knows what happened while it listened, and Twitch has no list
    of the latest subs or cheers, so a "latest subscriber" label stays empty until the next sub. StreamElements
    has listened for years. Read only, with his JWT; only kinds the toolbox knows nothing about are filled:
    what the toolbox saw itself is never replaced.

    With a `history` (the toolbox's own record) it also moves the past over, once per kind: how many and how
    much there was in all, who gave most and the biggest single one (cheers, tips), and the recent ones with
    their dates, so "this month" is right from the first day. After that StreamElements isn't needed for them."""

    def __init__(self, importer: StreamElementsImport, transport: httpx.AsyncBaseTransport | None = None,
                 history: EventHistory | None = None) -> None:
        self._importer = importer
        self._transport = transport
        self._history = history

    async def bring(self, session: WidgetSession) -> list[str]:
        """The kinds that were filled ("subscriber", "cheer", ...). PermissionError says what is missing."""
        token, channel = self._importer.credentials()
        async with web_client(self._transport, timeout=20) as client:
            answer = await client.get(f"{API}/{channel}", headers={"Authorization": f"Bearer {token}",
                                                                   "Accept": "application/json"})
        if answer.status_code in (401, 403):
            raise PermissionError("StreamElements refused the token (Connections → StreamElements)")
        answer.raise_for_status()
        found = answer.json()
        data = found.get("data") if isinstance(found, dict) and isinstance(found.get("data"), dict) else {}
        filled = []
        for kind in KINDS:
            entries = _entries(kind, data.get(f"{kind}-latest"), data.get(f"{kind}-recent"))
            moved = self._move(kind, data, entries)
            if not session.data[f"{kind}-latest"].get("name") and entries:
                session.know(kind, entries)
                moved = True
            if moved:
                filled.append(kind)
        session.refresh()
        return filled

    def _move(self, kind: str, data: dict[str, Any], entries: list[dict[str, Any]]) -> bool:
        """Their sums and dated recent ones into the toolbox's own record; only into a record that has nothing
        of that kind yet, and only once."""
        if self._history is None or self._history.known(kind):
            return False
        total = data.get(f"{kind}-total") if isinstance(data.get(f"{kind}-total"), dict) else {}
        counted = data.get(f"{kind}-count") if isinstance(data.get(f"{kind}-count"), dict) else {}
        count, amount = _number(counted.get("count", total.get("count"))), _number(total.get("amount"))
        if not (count or amount or entries):
            return False
        self._history.carry(kind, int(count), amount, data.get(f"{kind}-alltime-top-donator"),
                            data.get(f"{kind}-alltime-top-donation"))
        for entry in reversed(entries):
            when = _when(entry.get("createdAt"))
            if when:
                self._history.record(kind, entry["name"], _number(entry.get("amount")), at=when, counted=False,
                                     **{"from": "streamelements"})
        return True


def _number(value: Any) -> float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _when(text: Any) -> float:
    """A StreamElements date ("2026-09-09T18:58:12.969Z") as unix time, 0 if it isn't one."""
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def _entries(kind: str, latest: Any, recent: Any) -> list[dict[str, Any]]:
    """The newest ones of a kind, newest first, each with a name."""
    found = [dict(one) for one in recent if isinstance(one, dict) and one.get("name")] \
        if isinstance(recent, list) else []
    if isinstance(latest, dict) and latest.get("name") and (not found or found[0]["name"] != latest["name"]):
        found.insert(0, dict(latest))
    return [{"amount": 0, "message": "", **one, "type": kind} for one in found]
