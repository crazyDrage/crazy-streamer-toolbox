import json
import logging
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from streamer_toolbox.connections.twitch.twitch_clip_question import TwitchClipQuestion
from streamer_toolbox.core.web.web_client import web_client

log = logging.getLogger(__name__)
GQL = "https://gql.twitch.tv/gql"
WEB_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # the id twitch.tv's own page sends; public, no login
# the code of Twitch's stored question VideoAccessToken_Clip; the same one since at least 2021
TOKEN_QUERY = "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11"
# the same question written out, for the day that code is gone (tried 2026-10-09: Twitch answers it too)
WRITTEN_OUT = """query($slug: ID!) { clip(slug: $slug) {
  playbackAccessToken(params: {platform: "web", playerBackend: "mediaplayer", playerType: "site"}) { signature value }
  videoQualities { quality sourceURL } } }"""


class TwitchClipFiles:
    """Where a clip's video file is, so OBS can play it from there with no download. Twitch's official API
    (Helix) gives no file for other channels' clips, and Twitch's embed page puts a content warning with a
    button in front of many of them. So this asks the way twitch.tv's own player does: its internal GQL gives
    the clip's files per quality and a signature, and file + signature is a normal mp4 address (good for
    about 20 hours, so ask right before playing).

    **Unofficial**: Twitch can change it without notice (it is what yt-dlp and TwitchDownloaderCLI use). So it
    asks up to three ways, each only when the one before was refused (not when the clip is just unknown):

    1. Twitch's stored question by its code: one small request, the same since 2021.
    2. The same question written out: for when Twitch renewed the code.
    3. The question Twitch's own player uses right now, read from the player's code (TwitchClipQuestion; a
       few MB the first time, then kept for a week): for when Twitch changed the question itself. Only with
       `finder` on, since not everyone wants the toolbox to read Twitch's pages for this.

    If none is answered, files() fails with a plain reason and only the boxes built on it stop working."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 15.0,
                 question: TwitchClipQuestion | None = None) -> None:
        self._transport = transport
        self._timeout = timeout
        self._question = question

    async def files(self, clip: str, finder: bool = True) -> list[dict[str, Any]]:
        """[{quality, address}] of the clip (its id or its link), the best quality first. `finder` off: the
        third way to ask (see the class) is left out."""
        slug = clip_id(clip)
        if not slug:
            raise ValueError("which clip? (clip is empty)")
        stored = {"operationName": "VideoAccessToken_Clip", "variables": {"slug": slug, "platform": "web"},
                  "extensions": {"persistedQuery": {"version": 1, "sha256Hash": TOKEN_QUERY}}}
        try:
            async with web_client(self._transport, timeout=self._timeout) as client:
                body = await self._ask(client, stored)
                if _question_refused(body):
                    body = await self._ask(client, {"query": WRITTEN_OUT, "variables": {"slug": slug}})
                if _question_refused(body) and finder and self._question is not None:
                    body = await self._ask_as_the_player_does(client, slug) or body
            found = (body.get("data") or {}).get("clip")
        except (httpx.HTTPError, ValueError, AttributeError) as e:
            raise RuntimeError(f"Twitch gave no file for the clip {slug} ({e or type(e).__name__}): no "
                               "internet, or its way to ask has changed")
        if not found:
            if body.get("errors"):  # the request itself was refused, not this clip
                raise RuntimeError(f"Twitch gave no file for the clip {slug}: its way to ask may have changed "
                                   f"({str(body['errors'])[:120]})")
            raise RuntimeError(f"Twitch doesn't know the clip {slug} (deleted or private?)")
        token = found.get("playbackAccessToken") or {}
        refused = _refused(token.get("value", ""))
        if refused:
            raise RuntimeError(f"Twitch doesn't let this clip be played: {refused}")
        sign = f"?sig={token.get('signature', '')}&token={quote(token.get('value', ''))}"
        files = [{"quality": int(q["quality"]), "address": q["sourceURL"] + sign}
                 for q in found.get("videoQualities") or [] if q.get("sourceURL")]
        if not files:
            raise RuntimeError(f"Twitch has no video file for the clip {slug}")
        return sorted(files, key=lambda one: -one["quality"])

    @staticmethod
    async def _ask(client: httpx.AsyncClient, question: dict[str, Any]) -> dict[str, Any]:
        answer = await client.post(GQL, headers={"Client-ID": WEB_CLIENT_ID}, json=question)
        answer.raise_for_status()
        body = answer.json()
        return body if isinstance(body, dict) else {}

    async def _ask_as_the_player_does(self, client: httpx.AsyncClient, slug: str) -> dict[str, Any] | None:
        """Twitch's answer to the question its player uses now; None if that question can't be found. One
        that was kept from an earlier day and is refused is read anew once."""
        known = {"slug": slug, "platform": "web"}
        for again in (False, True):
            try:
                found = await self._question.find(again=again)
            except RuntimeError as e:
                log.warning("the question finder: %s", e)
                return None
            body = await self._ask(client, {"query": found["question"], "variables": {
                name: known[name] for name in found.get("variables") or [] if name in known}})
            if not _question_refused(body) or found.get("fresh"):
                return body
        return None


def clip_id(clip: str) -> str:
    """A clip's id from the id itself or from a link to it (clips.twitch.tv/<id>, twitch.tv/<name>/clip/<id>)."""
    text = str(clip).strip()
    if "/" in text:
        text = urlsplit(text if "://" in text else f"https://{text}").path.rstrip("/").rsplit("/", 1)[-1]
    return text


def _question_refused(body: dict[str, Any]) -> bool:
    """True when Twitch refused the question itself (not: it knows no such clip)."""
    return bool(body.get("errors")) and not (body.get("data") or {}).get("clip")


def _refused(token: str) -> str:
    """Why Twitch refuses the clip, "" if it doesn't (its token says so: authorization.forbidden)."""
    try:
        said = json.loads(token).get("authorization") or {}
    except (ValueError, AttributeError):
        return ""
    return (said.get("reason") or "no reason given") if said.get("forbidden") else ""
