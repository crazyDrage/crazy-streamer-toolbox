from typing import Any
from urllib.parse import urlencode

import httpx

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.core.web.web_client import web_client

ID = "https://id.twitch.tv/oauth2"
# the toolbox's own Twitch app ("crazy-streamer-tools", client type Public: it has no secret, so the id may be in
# the code). Used when no app of one's own is filled in; a public app logs in with a code (device code flow)
BUILT_IN_CLIENT_ID = "7fxa6gbrrpfuvxxmdg8tvpj9u6rdf7"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
PENDING = "authorization_pending"
SCOPES = ("channel:read:redemptions", "channel:manage:redemptions", "user:read:chat", "user:write:chat",
          "moderator:read:followers", "channel:read:subscriptions", "bits:read", "channel:read:ads",
          "channel:manage:broadcast")
# asked for at Connect too, but a login without them still works: only the boxes that need one say "press
# Connect once" (TwitchStreamActions). He said yes to all of them (2026-10-03); it's his account
EXTRA_SCOPES = ("clips:edit", "moderator:manage:shoutouts", "moderator:manage:announcements",
                "channel:manage:polls", "channel:manage:predictions", "channel:manage:raids",
                "channel:edit:commercial", "moderator:manage:chat_settings", "moderator:manage:banned_users",
                "moderator:read:chatters",
                # Get viewer role (TwitchViewerActions; his wish 2026-10-10): is this user a mod / a VIP of mine
                "moderation:read", "channel:read:vips",
                # the trigger Suspicious user wrote (his go 2026-10-11): Twitch's "ban evader" note on a chatter
                "moderator:read:suspicious_users")


class TwitchAuth:
    """Twitch login (dev.twitch.tv/docs/authentication), two ways. An app with a secret (one's own,
    "Confidential"): the authorization code flow: the streamer allows the app in the browser, Twitch sends the
    browser back to redirect_uri with a code, the code becomes tokens. An app without a secret ("Public", the
    toolbox's built-in one): the device code flow: Twitch gives a short code and a page, the streamer confirms
    the code there, and the toolbox asks until the tokens are there. A public app's refresh token works once:
    every renewal brings a new one that has to be kept."""

    @property
    def public(self) -> bool:
        return not self._client_secret

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._transport = transport

    def authorize_url(self, state: str) -> str:
        return f"{ID}/authorize?" + urlencode({"response_type": "code", "client_id": self.client_id,
                                               "redirect_uri": self.redirect_uri, "scope": " ".join(SCOPES + EXTRA_SCOPES),
                                               "state": state, "force_verify": "true"})

    async def exchange(self, code: str) -> dict[str, Any]:
        return await self._token({"grant_type": "authorization_code", "code": code,
                                  "redirect_uri": self.redirect_uri})

    async def device(self) -> dict[str, Any]:
        """Starts a login with a code: {device_code, user_code, verification_uri, interval, expires_in}."""
        async with web_client(self._transport, timeout=10) as client:
            response = await client.post(f"{ID}/device", data={"client_id": self.client_id,
                                                               "scopes": " ".join(SCOPES + EXTRA_SCOPES)})
        return _json(response)

    async def device_token(self, device_code: str) -> dict[str, Any] | None:
        """The tokens once he confirmed the code; None while Twitch still waits for him."""
        try:
            return await self._token({"grant_type": DEVICE_GRANT, "device_code": device_code,
                                      "scopes": " ".join(SCOPES + EXTRA_SCOPES)})
        except TwitchApiError as e:
            if PENDING in str(e):
                return None
            raise

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        return await self._token({"grant_type": "refresh_token", "refresh_token": refresh_token})

    async def validate(self, access_token: str) -> dict[str, Any]:
        """{client_id, login, user_id, scopes, expires_in}; raises TwitchApiError(401) for a dead token."""
        async with web_client(self._transport, timeout=10) as client:
            response = await client.get(f"{ID}/validate", headers={"Authorization": f"OAuth {access_token}"})
        return _json(response)

    async def _token(self, data: dict[str, str]) -> dict[str, Any]:
        async with web_client(self._transport, timeout=10) as client:
            secret = {} if self.public else {"client_secret": self._client_secret}
            response = await client.post(f"{ID}/token", data={"client_id": self.client_id, **secret, **data})
        return _json(response)


def _json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text
        raise TwitchApiError(response.status_code, message)
    return response.json()
