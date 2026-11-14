import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.widgets.kept_answers import KeptAnswers

log = logging.getLogger(__name__)
Helix = Callable[..., Awaitable[dict[str, Any]]]
KEEP_COUNT = 5000  # people; ~120 bytes each in the file
KEEP_SECONDS = 24 * 60 * 60  # then Twitch is asked again (a new picture shows the next day)
WAIT = 0.15  # seconds the questions of many new chatters are gathered into one request
MOST = 100  # users per Helix request
SIZES = ("70x70", "150x150", "300x300")  # Twitch keeps each profile picture in these sizes


class TwitchPictureLookup:
    """A Twitch user's profile picture address (his note temp/notes/humam/twitch-pfp.md): Helix `users` by id (or
    by name), only Twitch itself. The address is kept for a day, in memory and in `path` (a restart keeps it).
    New people asked within WAIT go to Twitch in one request (up to MOST each); the same person asked twice
    at once is one question. When Twitch can't be reached, an address kept before is used even when old;
    without one the answer is "" (never an error: a chat must go on). The picture itself isn't downloaded:
    the page loads it from Twitch, and the browser keeps it."""

    def __init__(self, helix: Helix, path: Path | None = None, wait: float = WAIT,
                 kept: KeptAnswers | None = None) -> None:
        self._helix = helix
        self._kept = kept if kept is not None else KeptAnswers(path, KEEP_COUNT, KEEP_SECONDS)
        self._wait = wait
        self._waiting: dict[str, asyncio.Future] = {}
        self._batch: asyncio.Task | None = None

    async def picture(self, user: Any, size: str = SIZES[0]) -> str:
        """The address of user's picture (a Twitch user id, or a name), in that size; "" when there is none."""
        key = _key(user)
        if not key:
            return ""
        found, address = self._kept.get(key)
        if not found:
            address = await self._ask(key)
        return _sized(address or "", size)

    def _ask(self, key: str) -> asyncio.Future:
        if key not in self._waiting:
            self._waiting[key] = asyncio.get_running_loop().create_future()
        if self._batch is None or self._batch.done():
            self._batch = asyncio.create_task(self._send_soon())
        return asyncio.shield(self._waiting[key])

    async def _send_soon(self) -> None:
        await asyncio.sleep(self._wait)
        while self._waiting:
            asked = dict(list(self._waiting.items())[:MOST])
            for key in asked:
                del self._waiting[key]
            answers = await self._from_twitch(list(asked))
            for key, future in asked.items():
                if not future.done():
                    future.set_result(answers.get(key, ""))

    async def _from_twitch(self, keys: list[str]) -> dict[str, str]:
        ids = [key[3:] for key in keys if key.startswith("id:")]
        logins = [key[6:] for key in keys if key.startswith("login:")]
        try:
            answer = await self._helix("GET", "users", params={**({"id": ids} if ids else {}),
                                                               **({"login": logins} if logins else {})})
        except Exception as e:  # Twitch down, not connected, a token gone: the old addresses, else none
            log.warning("no Twitch profile pictures this time: %s", e)
            return {key: self._kept.old(key)[1] or "" for key in keys}
        found = {key: "" for key in keys}  # asked and not there: kept too, so it isn't asked again today
        for user in answer.get("data") or [] if isinstance(answer, dict) else []:
            address = str(user.get("profile_image_url") or "")
            found[f"id:{user.get('id', '')}"] = address
            found[f"login:{str(user.get('login', '')).lower()}"] = address
        self._kept.keep_all(found)
        return found


def _key(user: Any) -> str:
    """"id:<id>" for a Twitch user id (digits), "login:<name>" for a name; "" for nothing usable."""
    text = str(user if user is not None else "").strip().lstrip("@").lower()
    if text.isdigit():
        return f"id:{text}"
    return f"login:{text}" if text and text.replace("_", "").isalnum() else ""


def _sized(address: str, size: str) -> str:
    """Twitch's address names its size (…-profile_image-300x300.png): the one asked for instead."""
    if size not in SIZES:
        return address
    for other in SIZES:
        if f"-{other}." in address:
            return address.replace(f"-{other}.", f"-{size}.")
    return address
