import json
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.widgets.widget_session import WidgetSession

Helix = Callable[..., Awaitable[dict[str, Any]]]
log = logging.getLogger(__name__)
SUBSCRIBED = ("twitch.sub", "twitch.resub")
PAGES = 50  # 5000 subscribers; a bigger channel is only partly compared


class MissedSubscribers:
    """Finds who subscribed while the toolbox was off. Twitch only tells a new sub at the moment it happens,
    and has no dated list. But it does list who is subscribed now (Get Broadcaster Subscriptions). So the
    toolbox keeps the list it saw last (config/history/subscribers.json); at start, check() asks for the list
    again, and a name that wasn't there before is a sub it missed: written into the record (marked `missed`,
    dated now: when it really happened isn't known) and shown as the latest subscriber. Subs that come in while
    the toolbox runs are added to the kept list as they happen (handle), so they aren't found a second time.

    The first check only keeps the list: nobody is "missed" before the toolbox ever looked. Someone whose
    sub ran out and who subscribed again while it was off is found; a renewal isn't (the name was there)."""

    def __init__(self, helix: Helix, own: Callable[[], dict[str, str]], session: WidgetSession,
                 history: EventHistory, path: Path) -> None:
        self._helix = helix
        self._own = own  # gives "providerId": the streamer's Twitch id
        self._session = session
        self._history = history
        self._path = path

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        """EventBus: a sub the toolbox saw itself goes onto the kept list."""
        login = str(data.get("user_login") or "").casefold()
        if kind in SUBSCRIBED and login:
            seen = self._seen()
            if seen is not None and login not in seen:
                self._keep(seen | {login})

    async def check(self) -> list[str]:
        """The names of the subs that were missed (none the first time, or when Twitch can't be asked)."""
        twitch_id = str(self._own().get("providerId") or "")
        if not twitch_id:
            return []
        try:
            now = await self._subscribers(twitch_id)
        except Exception as e:  # not logged in, not an affiliate, Twitch down
            log.info("missed subs: Twitch's list was not read (%s)", e)
            return []
        seen = self._seen()
        self._keep(set(now))
        if seen is None:
            return []
        missed = [name for login, name in now.items() if login not in seen]
        if missed:
            stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            entries = [{"type": "subscriber", "name": name, "amount": 1, "message": "", "createdAt": stamp}
                       for name in missed]
            for name in missed:
                self._history.record("subscriber", name, 1, missed=True)
            self._session.know("subscriber", [*entries, *self._session.data["subscriber-recent"]])
            self._session.refresh()
        return missed

    async def _subscribers(self, twitch_id: str) -> dict[str, str]:
        """login → name of everyone subscribed now, without the streamer himself."""
        found: dict[str, str] = {}
        cursor = ""
        for _ in range(PAGES):
            answer = await self._helix("GET", "subscriptions", params={
                "broadcaster_id": twitch_id, "first": 100, **({"after": cursor} if cursor else {})})
            for one in answer.get("data") or []:
                login = str(one.get("user_login") or "").casefold()
                if login and str(one.get("user_id")) != twitch_id:
                    found[login] = str(one.get("user_name") or login)
            cursor = str((answer.get("pagination") or {}).get("cursor") or "")
            if not cursor:
                break
        return found

    def _seen(self) -> set[str] | None:
        try:
            kept = json.loads(self._path.read_text(encoding="utf-8")) if self._path.is_file() else None
        except ValueError:
            return None
        return {str(login) for login in kept} if isinstance(kept, list) else None

    def _keep(self, logins: set[str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(sorted(logins)), encoding="utf-8")
