from typing import Any
from urllib.parse import urlencode

import httpx

from streamer_toolbox.connections.youtube.youtube_api_error import YouTubeApiError
from streamer_toolbox.core.web.web_client import web_client

AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
READ = "https://www.googleapis.com/auth/youtube.readonly"  # see his broadcasts and their chat
# send chat messages. Google has no smaller permission for that: this one may manage the whole YouTube account,
# so it is only asked for when he switches "May write in chat" on
WRITE = "https://www.googleapis.com/auth/youtube.force-ssl"


class YouTubeAuth:
    """Google login with the authorization code flow (developers.google.com/identity/protocols/oauth2): he
    allows his own Google Cloud app in the browser, Google sends the browser back to redirect_uri with a code,
    the code becomes tokens. access_type=offline + prompt=consent make Google hand out a refresh token."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._transport = transport

    def authorize_url(self, state: str, write: bool = False) -> str:
        return f"{AUTHORIZE}?" + urlencode({
            "response_type": "code", "client_id": self.client_id, "redirect_uri": self.redirect_uri,
            "scope": " ".join((READ, WRITE) if write else (READ,)), "state": state,
            "access_type": "offline", "prompt": "consent"})

    async def exchange(self, code: str) -> dict[str, Any]:
        return await self._token({"grant_type": "authorization_code", "code": code,
                                  "redirect_uri": self.redirect_uri})

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Google's answer to a refresh has no new refresh token: the old one stays."""
        return await self._token({"grant_type": "refresh_token", "refresh_token": refresh_token})

    async def _token(self, data: dict[str, str]) -> dict[str, Any]:
        async with web_client(self._transport, timeout=10) as client:
            response = await client.post(TOKEN, data={"client_id": self.client_id,
                                                      "client_secret": self._client_secret, **data})
        if response.status_code >= 400:
            try:
                told = response.json()
                message = told.get("error_description") or told.get("error") or response.text
            except ValueError:
                message = response.text
            raise YouTubeApiError(response.status_code, str(message))
        return response.json()
