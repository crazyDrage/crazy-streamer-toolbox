from typing import Any
from urllib.parse import parse_qs

import httpx

READ = "https://www.googleapis.com/auth/youtube.readonly"
WRITE = "https://www.googleapis.com/auth/youtube.force-ssl"


class FakeYouTube:
    """Google's token address and the YouTube API calls the toolbox uses, from a script. `broadcast` is the
    stream that is live (None = not live); `pages` are the chat's answers in order (the last one repeats; an
    httpx.Response is given as it is); `scope` is what a login grants; `not_enabled` answers as for a
    channel without live streaming. Every call is kept."""

    def __init__(self) -> None:
        self.broadcast: dict[str, Any] | None = None
        self.not_enabled = False  # the channel never switched live streaming on
        self.pages: list[Any] = [{"items": [], "nextPageToken": "p1", "pollingIntervalMillis": 0}]
        self.scope = READ
        self.valid = {"access-1"}
        self.refresh_ok = True
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.sent: list[dict[str, Any]] = []
        self.transport = httpx.MockTransport(self._answer)

    def _answer(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.url.host == "oauth2.googleapis.com":
            form = {key: value[0] for key, value in parse_qs(request.content.decode()).items()}
            self.calls.append(("POST", "token", form))
            if form["grant_type"] == "refresh_token":
                if not self.refresh_ok:
                    return httpx.Response(400, json={"error": "invalid_grant", "error_description": "revoked"})
                self.valid.add("access-2")
                return httpx.Response(200, json={"access_token": "access-2", "expires_in": 3600, "scope": self.scope})
            self.valid.add("access-2")
            return httpx.Response(200, json={"access_token": "access-2", "refresh_token": "refresh-2",
                                             "expires_in": 3600, "scope": self.scope})
        name = path.removeprefix("/youtube/v3/")
        self.calls.append((request.method, name, dict(request.url.params)))
        if request.headers.get("authorization", "").removeprefix("Bearer ") not in self.valid:
            return httpx.Response(401, json={"error": {"message": "Invalid Credentials",
                                                       "errors": [{"reason": "authError"}]}})
        if name == "channels":
            return httpx.Response(200, json={"items": [{"id": "UC1", "snippet": {"title": "crazyDrage"}}]})
        if name == "liveBroadcasts" and self.not_enabled:
            return httpx.Response(403, json={"error": {"message": "The user is not enabled for live streaming.",
                                                       "errors": [{"reason": "liveStreamingNotEnabled"}]}})
        if name == "liveBroadcasts":
            return httpx.Response(200, json={"items": [self.broadcast] if self.broadcast else []})
        if name == "liveChat/messages" and request.method == "POST":
            self.sent.append(__import__("json").loads(request.content))
            return httpx.Response(200, json={"id": "m-sent"})
        if name == "liveChat/messages":
            page = self.pages.pop(0) if len(self.pages) > 1 else self.pages[0]
            return page if isinstance(page, httpx.Response) else httpx.Response(200, json=page)
        return httpx.Response(404, json={"error": {"message": "not found", "errors": [{"reason": "notFound"}]}})
