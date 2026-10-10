import json
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from streamer_toolbox.connections.twitch.graphql_document import find_document, to_query, variables_of
from streamer_toolbox.core.web.web_client import web_client

log = logging.getLogger(__name__)
PLAYER_PAGE = "https://clips.twitch.tv/embed?clip=a&parent=localhost"  # the clip player; any clip name will do
CODE_FILE = re.compile(r"https://(?:assets\.twitch\.tv|static\.twitchcdn\.net)/assets/[\w.-]+\.js")
OPERATION = "VideoAccessToken_Clip"
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}
MAX_FILES = 120
MAX_BYTES = 6_000_000  # per code file; the one that holds the question is a few hundred KB
WEEK = 7 * 24 * 60 * 60


class TwitchClipQuestion:
    """Finds out how Twitch's own clip player asks for a clip's files right now: the last thing to try when
    Twitch no longer answers the two ways the toolbox knows by heart (TwitchClipFiles).

    It reads the player page, then the page's code files one after another until one holds the question
    `VideoAccessToken_Clip` (packed as a parsed document), and writes it out as text again
    (graphql_document). Nothing of that code is run: it is only read as text, and only from Twitch's own
    two addresses for its code. It is slow (a few MB the first time), so what was found is kept in a file for a
    week; find(again=True) reads the player anew."""

    def __init__(self, keep: Path | None = None, transport: httpx.AsyncBaseTransport | None = None,
                 now: Callable[[], float] = time.time, keep_for: float = WEEK) -> None:
        self._keep = keep
        self._transport = transport
        self._now = now
        self._keep_for = keep_for
        self._found: dict[str, Any] = {}

    async def find(self, again: bool = False) -> dict[str, Any]:
        """{question, variables (the names it asks for), found (when), fresh (read just now)}. RuntimeError
        when the player doesn't hold it (any more)."""
        kept = self._found or self._read()
        if kept and not again and self._now() - float(kept.get("found", 0)) < self._keep_for:
            return {**kept, "fresh": False}
        try:
            async with web_client(self._transport, timeout=20, headers=BROWSER,
                                         follow_redirects=True) as client:
                page = await client.get(PLAYER_PAGE)
                page.raise_for_status()
                files = list(dict.fromkeys(CODE_FILE.findall(page.text)))[:MAX_FILES]
                for address in files:
                    code = await self._code(client, address)
                    document = find_document(code, OPERATION) if OPERATION in code else None
                    if document is not None:
                        self._found = {"question": to_query(document), "found": self._now(), "from": address,
                                       "variables": variables_of(document, OPERATION)}
                        self._write(self._found)
                        log.info("Twitch's clip question read from %s", address)
                        return {**self._found, "fresh": True}
        except (httpx.HTTPError, ValueError) as e:
            raise RuntimeError(f"Twitch's player could not be read ({e or type(e).__name__})") from None
        raise RuntimeError(f"Twitch's player doesn't hold the question {OPERATION} any more "
                           f"({len(files)} code files read)")

    @staticmethod
    async def _code(client: httpx.AsyncClient, address: str) -> str:
        """A code file's text; "" for one that is too big or doesn't come."""
        try:
            async with client.stream("GET", address) as answer:
                if answer.status_code != 200 or int(answer.headers.get("content-length") or 0) > MAX_BYTES:
                    return ""
                parts, size = [], 0
                async for part in answer.aiter_bytes():
                    size += len(part)
                    if size > MAX_BYTES:
                        return ""
                    parts.append(part)
        except httpx.HTTPError:
            return ""
        return b"".join(parts).decode("utf-8", errors="replace")

    def _read(self) -> dict[str, Any]:
        if self._keep is None:
            return {}
        try:
            kept = json.loads(self._keep.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return kept if isinstance(kept, dict) and kept.get("question") else {}

    def _write(self, found: dict[str, Any]) -> None:
        if self._keep is not None:
            self._keep.parent.mkdir(parents=True, exist_ok=True)
            self._keep.write_text(json.dumps(found, indent=1), encoding="utf-8")
