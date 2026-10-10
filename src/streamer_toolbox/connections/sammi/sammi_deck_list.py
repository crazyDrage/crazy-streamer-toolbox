import time
from collections.abc import Awaitable, Callable
from typing import Any

Fetch = Callable[[], Awaitable[Any]]


class SammiDeckList:
    """SAMMI's decks and their buttons, read with the Local API's getDeckList (not in SAMMI's docs, but SAMMI
    lists it among its GET requests). Kept for a few seconds, so one box form with several button fields asks
    SAMMI once; every form opened later gets a fresh list, so new or renamed buttons show up by themselves."""

    def __init__(self, fetch: Fetch, keep_seconds: float = 5.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._fetch = fetch
        self._keep = keep_seconds
        self._clock = clock
        self._decks: list[dict[str, Any]] = []
        self._read_at: float | None = None

    async def decks(self) -> list[dict[str, Any]]:
        if self._read_at is None or self._clock() - self._read_at > self._keep:
            self._decks = list(await self._fetch() or [])
            self._read_at = self._clock()
        return self._decks

    async def button_groups(self) -> dict[str, dict[str, str]]:
        """deck name → {button ID → "text [ID]"}: the button field gets a deck picker in front."""
        groups: dict[str, dict[str, str]] = {}
        for deck in await self.decks():
            items = groups.setdefault(deck.get("deckName", "?"), {})
            for button in deck.get("buttons", []):
                text = " ".join(str(button.get("text", "")).split()) or "(no text)"
                items[button["id"]] = f"{text}  [{button['id']}]"
        return groups

    async def deck_choices(self) -> dict[str, str]:
        """deck ID → deck name."""
        return {deck["deckId"]: deck.get("deckName", deck["deckId"]) for deck in await self.decks()}

    async def summary(self) -> list[dict[str, Any]]:
        """Each deck: name, id, on/off and its buttons (id + text), for a flow or the Live page."""
        return [{"name": d.get("deckName", ""), "id": d["deckId"], "enabled": bool(d.get("status")),
                 "buttons": [{"id": b["id"], "text": b.get("text", "")} for b in d.get("buttons", [])]}
                for d in await self.decks()]
