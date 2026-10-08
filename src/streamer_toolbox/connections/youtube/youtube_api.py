from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from streamer_toolbox.connections.youtube.youtube_api_error import YouTubeApiError

API = "https://www.googleapis.com/youtube/v3"


class YouTubeApi:
    """The YouTube Data / Live Streaming API calls the toolbox uses, as the logged-in streamer
    (developers.google.com/youtube/v3/live/docs). token() gives a fresh access token; after a 401 it's asked
    once more with renew=True. Every call costs points of the Google project's daily quota (10 000 by default)."""

    def __init__(self, token: Callable[..., Awaitable[str]], transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token = token
        self._transport = transport

    async def channel(self) -> dict[str, str]:
        """His channel: {"id", "title"}."""
        items = (await self._call("GET", "channels", params={"part": "snippet", "mine": "true"})).get("items") or []
        if not items:
            raise YouTubeApiError(404, "this Google account has no YouTube channel")
        return {"id": str(items[0].get("id", "")), "title": str(items[0].get("snippet", {}).get("title", ""))}

    async def live_chat(self) -> dict[str, str] | None:
        """The stream that is live right now: {"chat", "title", "video"}; None when he isn't live."""
        answer = await self._call("GET", "liveBroadcasts", params={
            "part": "snippet", "broadcastStatus": "active", "broadcastType": "all"})
        for item in answer.get("items") or []:
            snippet = item.get("snippet", {})
            if snippet.get("liveChatId"):
                return {"chat": str(snippet["liveChatId"]), "title": str(snippet.get("title", "")),
                        "video": str(item.get("id", ""))}
        return None

    async def chat_messages(self, chat: str, page: str = "") -> dict[str, Any]:
        """One answer of the chat: {"items", "nextPageToken", "pollingIntervalMillis"}. Without a page token it
        holds the recent history. A chat that ended raises YouTubeApiError with reason liveChatEnded."""
        return await self._call("GET", "liveChat/messages", params={
            "liveChatId": chat, "part": "snippet,authorDetails", "maxResults": "200",
            **({"pageToken": page} if page else {})})

    async def send_chat(self, chat: str, message: str) -> None:
        await self._call("POST", "liveChat/messages", params={"part": "snippet"}, json={"snippet": {
            "liveChatId": chat, "type": "textMessageEvent", "textMessageDetails": {"messageText": message}}})

    async def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._send(method, path, await self._token(), **kwargs)
        if response.status_code == 401:
            response = await self._send(method, path, await self._token(renew=True), **kwargs)
        if response.status_code >= 400:
            try:
                error = response.json().get("error", {})
                reason = str((error.get("errors") or [{}])[0].get("reason", ""))
                message = str(error.get("message") or response.text)
            except (ValueError, AttributeError, IndexError):
                reason, message = "", response.text
            raise YouTubeApiError(response.status_code, message, reason)
        return response.json() if response.content else {}

    async def _send(self, method: str, path: str, token: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(transport=self._transport, timeout=10) as client:
            return await client.request(method, f"{API}/{path}", headers={"Authorization": f"Bearer {token}"},
                                        **kwargs)
